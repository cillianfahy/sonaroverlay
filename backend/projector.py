from typing import Optional, Tuple
import numpy as np
import cv2
from .models import ExtrinsicsModel, OverlayOptionsModel
from . import config


class Projector:
    def __init__(self) -> None:
        self.K: Optional[np.ndarray] = None
        self.dist: Optional[np.ndarray] = None
        self.image_size: Optional[Tuple[int, int]] = None
        self.rvec = np.zeros((3, 1), dtype=np.float32)
        self.tvec = np.zeros((3, 1), dtype=np.float32)
        self.overlay = config.load_overlay_options()
        K, dist, size = config.load_camera_intrinsics()
        if K is not None:
            self.set_intrinsics(K, dist, size)
        self.set_extrinsics(config.load_extrinsics())

    def set_intrinsics(self, K: np.ndarray, dist: np.ndarray, image_size: Tuple[int, int]) -> None:
        self.K = K.astype(np.float32)
        self.dist = dist.astype(np.float32).reshape(-1, 1)
        self.image_size = image_size

    def set_extrinsics(self, model: ExtrinsicsModel) -> None:
        self.rvec = np.array(model.rvec, dtype=np.float32).reshape(3, 1)
        self.tvec = np.array(model.tvec, dtype=np.float32).reshape(3, 1)

    def set_overlay_options(self, model: OverlayOptionsModel) -> None:
        self.overlay = model

    def project_points(self, points_sonar_xyz: np.ndarray) -> Optional[np.ndarray]:
        """
        points_sonar_xyz: (N,3) in sonar frame. Convert to camera with extrinsics (R,t) already defined as sonar->camera.
        Then project using camera intrinsics/distortion.
        """
        if self.K is None or self.dist is None:
            return None
        # Transform: Xc = R @ Xs + t, where rvec/tvec represent sonar->camera
        # cv2.projectPoints expects object points in the object frame and rvec/tvec to camera.
        pts = points_sonar_xyz.astype(np.float32).reshape(-1, 1, 3)
        uv, _ = cv2.projectPoints(pts, self.rvec, self.tvec, self.K, self.dist)
        return uv.reshape(-1, 2)

    def draw_overlay(self, frame_bgr: np.ndarray, uv: np.ndarray, depths_m: np.ndarray) -> np.ndarray:
        if not self.overlay.enabled:
            return frame_bgr
        h, w = frame_bgr.shape[:2]
        dec = max(1, int(self.overlay.decimate))
        ps = int(self.overlay.point_size)
        # Color by range (near=red to far=blue)
        if depths_m.size > 0:
            dmin, dmax = float(np.min(depths_m)), float(np.max(depths_m))
            denom = (dmax - dmin) if (dmax - dmin) > 1e-6 else 1.0
        else:
            dmin, dmax, denom = 0.0, 1.0, 1.0
        for i in range(0, uv.shape[0], dec):
            x, y = int(uv[i, 0]), int(uv[i, 1])
            if x < 0 or y < 0 or x >= w or y >= h:
                continue
            t = (float(depths_m[i]) - dmin) / denom
            # simple colormap: red->yellow->green->cyan->blue
            color = (int(255 * (1 - t)), int(255 * t), 255 - int(255 * abs(t - 0.5) * 2))
            cv2.circle(frame_bgr, (x, y), ps, color, -1)
        return frame_bgr


_PROJECTOR: Optional[Projector] = None


def get_projector() -> Projector:
    global _PROJECTOR
    if _PROJECTOR is None:
        _PROJECTOR = Projector()
    return _PROJECTOR


