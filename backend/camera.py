import threading
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np
from . import config
from .projector import get_projector
from .sonar_rip2 import get_sonar_manager


def enumerate_cameras(max_index: int = 10) -> List[dict]:
    devices = []
    for idx in range(max_index + 1):
        cap = cv2.VideoCapture(idx)
        if cap is not None and cap.isOpened():
            devices.append({"index": idx, "name": f"Camera {idx}"})
            cap.release()
    return devices


class CameraManager:
    def __init__(self) -> None:
        self.device_index: Optional[int] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_lock = threading.Lock()
        self.latest_frame_bgr: Optional[np.ndarray] = None
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def select_device(self, idx: int) -> bool:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            return False
        # reasonable defaults
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap = cap
        self.device_index = idx
        return True

    def _loop(self) -> None:
        while self.running:
            if self.cap is None:
                time.sleep(0.05)
                continue
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self.frame_lock:
                self.latest_frame_bgr = frame

    def get_frame_raw(self) -> Optional[np.ndarray]:
        with self.frame_lock:
            if self.latest_frame_bgr is None:
                return None
            return self.latest_frame_bgr.copy()

    def get_frame_with_overlay(self) -> Optional[np.ndarray]:
        frame = self.get_frame_raw()
        if frame is None:
            return None
        proj = get_projector()
        # Draw sonar overlay if points available and intrinsics present
        points_xyz, depths = get_sonar_manager().get_latest_points()
        if points_xyz is not None and proj.K is not None:
            uv = proj.project_points(points_xyz)
            if uv is not None:
                frame = proj.draw_overlay(frame, uv, depths)
        return frame


_CAMERA_MANAGER: Optional[CameraManager] = None


def get_camera_manager() -> CameraManager:
    global _CAMERA_MANAGER
    if _CAMERA_MANAGER is None:
        _CAMERA_MANAGER = CameraManager()
    return _CAMERA_MANAGER


