import socket
import struct
import threading
import time
from typing import Optional, Tuple
import numpy as np
import snappy
from .models import SonarConfigModel

# Try to import compiled proto if available
try:
    from .proto import waterlinked_sonar_pb2 as wl_pb2  # type: ignore
    _PROTO_AVAILABLE = True
except Exception:
    # Try to compile on the fly if grpc_tools is available
    try:
        import os
        from grpc_tools import protoc  # type: ignore
        here = os.path.dirname(__file__)
        proto_dir = os.path.join(here, "proto")
        proto_path = os.path.join(proto_dir, "waterlinked_sonar.proto")
        if os.path.exists(proto_path):
            protoc.main([
                "protoc",
                f"-I{proto_dir}",
                f"--python_out={proto_dir}",
                proto_path,
            ])
            from .proto import waterlinked_sonar_pb2 as wl_pb2  # type: ignore
            _PROTO_AVAILABLE = True
        else:
            _PROTO_AVAILABLE = False
    except Exception:
        _PROTO_AVAILABLE = False

MAGIC = b"\x82\x73\x80\x50"  # "RIP2"


def _crc32_ieee8023(data: bytes) -> int:
    # Placeholder: real IEEE 802.3 CRC-32 check would be implemented or delegated.
    # For now, skip strict CRC validation to avoid dropping packets if implementation is missing.
    return 0


class SonarManager:
    def __init__(self) -> None:
        self.cfg = SonarConfigModel()
        self.sock: Optional[socket.socket] = None
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.seq_last: Optional[int] = None
        self.packets_received = 0
        self.last_rx_time = 0.0
        # Latest points in sonar frame
        self.points_xyz: Optional[np.ndarray] = None
        self.depths_m: Optional[np.ndarray] = None
        self.thread.start()

    def get_config(self) -> SonarConfigModel:
        return self.cfg

    def apply_config(self, cfg: SonarConfigModel) -> None:
        self.cfg = cfg
        self._reset_socket()

    def get_stats(self) -> dict:
        return {
            "packets_received": self.packets_received,
            "last_rx_time": self.last_rx_time,
            "proto_available": _PROTO_AVAILABLE,
        }

    def _reset_socket(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def _ensure_socket(self) -> None:
        if not self.cfg.enabled:
            return
        if self.sock is not None:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", self.cfg.port))
        except OSError:
            # macOS may require binding to multicast addr explicitly
            s.bind((self.cfg.multicast_addr, self.cfg.port))
        mreq = struct.pack("=4sl", socket.inet_aton(self.cfg.multicast_addr), socket.INADDR_ANY)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        s.settimeout(0.5)
        self.sock = s

    def _loop(self) -> None:
        while self.running:
            try:
                self._ensure_socket()
                if self.sock is None:
                    time.sleep(0.2)
                    continue
                try:
                    data, _ = self.sock.recvfrom(65535)
                except socket.timeout:
                    continue
                self.last_rx_time = time.time()
                self.packets_received += 1
                self._handle_packet(data)
            except Exception:
                # Keep running on errors
                time.sleep(0.05)

    def _handle_packet(self, packet: bytes) -> None:
        if len(packet) < 12:
            return
        if packet[:4] != MAGIC:
            return
        length = struct.unpack(">I", packet[4:8])[0]
        if length != len(packet):
            return
        payload = packet[8:-4]
        # crc = struct.unpack(">I", packet[-4:])[0]
        # Skipping CRC check in this bootstrap
        try:
            decompressed = snappy.uncompress(payload)
        except Exception:
            return
        if not _PROTO_AVAILABLE:
            # Without proto we cannot decode; leave points empty
            return
        try:
            pkt = wl_pb2.Packet()
            pkt.ParseFromString(decompressed)
            # Identify RangeImage
            type_url = pkt.msg.type_url
            if "RangeImage" not in type_url:
                return
            range_img = wl_pb2.RangeImage()
            pkt.msg.Unpack(range_img)
            self._range_image_to_points(range_img)
        except Exception:
            return

    def _range_image_to_points(self, ri) -> None:
        W = int(ri.width)
        H = int(ri.height)
        fovH = float(ri.fov_horizontal)
        fovV = float(ri.fov_vertical)
        scale = float(ri.image_pixel_scale)
        # image_pixel_data may be repeated uint32; interpret as 16-bit values
        arr = np.array(ri.image_pixel_data, dtype=np.uint32).reshape(-1)
        # Clip to 16-bit
        r16 = (arr & 0xFFFF).astype(np.uint16)
        if r16.size < W * H:
            return
        r16 = r16[: W * H].reshape(H, W)
        # Build pixel grids
        xs = np.arange(W, dtype=np.float32)
        ys = np.arange(H, dtype=np.float32)
        px, py = np.meshgrid(xs, ys)
        yaw = (px / max(W - 1, 1) * fovH - (fovH / 2.0)).astype(np.float32)
        pitch = (py / max(H - 1, 1) * fovV - (fovV / 2.0)).astype(np.float32)
        r = r16.astype(np.float32) * scale
        mask = r > 0.0
        yaw = np.deg2rad(yaw[mask])
        pitch = np.deg2rad(pitch[mask])
        r = r[mask]
        x = r * np.cos(pitch) * np.cos(yaw)
        y = r * np.cos(pitch) * np.sin(yaw)
        z = -r * np.sin(pitch)
        pts = np.stack([x, y, z], axis=1)
        self.points_xyz = pts
        self.depths_m = r

    def get_latest_points(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        return self.points_xyz, self.depths_m if self.depths_m is not None else (None, None)


_SONAR_MANAGER: Optional[SonarManager] = None


def get_sonar_manager() -> SonarManager:
    global _SONAR_MANAGER
    if _SONAR_MANAGER is None:
        _SONAR_MANAGER = SonarManager()
    return _SONAR_MANAGER


