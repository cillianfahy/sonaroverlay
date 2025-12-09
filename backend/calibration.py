from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np
from .models import CalibStatusResponse


@dataclass
class CalibResult:
    ok: bool
    rms_error: float
    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    image_size: Tuple[int, int]


class Calibrator:
    def __init__(self) -> None:
        self.collecting = False
        self.rows = 0
        self.cols = 0
        self.square_size_m = 0.0
        self.objpoints: List[np.ndarray] = []
        self.imgpoints: List[np.ndarray] = []
        self.image_size: Optional[Tuple[int, int]] = None

    def start(self, rows: int, cols: int, square_size_m: float) -> None:
        self.collecting = True
        self.rows = rows
        self.cols = cols
        self.square_size_m = square_size_m
        self.objpoints.clear()
        self.imgpoints.clear()
        self.image_size = None

    def status(self) -> CalibStatusResponse:
        return CalibStatusResponse(
            collecting=self.collecting,
            num_samples=len(self.imgpoints),
            target_rows=self.rows,
            target_cols=self.cols,
            square_size_m=self.square_size_m,
        )

    def _chessboard_corners(self, gray: np.ndarray) -> Optional[np.ndarray]:
        pattern_size = (self.cols, self.rows)
        flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE
        ok, corners = cv2.findChessboardCorners(gray, pattern_size, flags)
        if not ok:
            return None
        # refine
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners_refined = cv2.cornerSubPix(
            gray, corners, winSize=(11, 11), zeroZone=(-1, -1), criteria=criteria
        )
        return corners_refined

    def capture(self, frame_bgr: np.ndarray) -> bool:
        if not self.collecting:
            return False
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        corners = self._chessboard_corners(gray)
        if corners is None:
            return False
        # build object points
        objp = np.zeros((self.rows * self.cols, 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.cols, 0:self.rows].T.reshape(-1, 2)
        objp *= float(self.square_size_m)
        self.objpoints.append(objp)
        self.imgpoints.append(corners)
        self.image_size = (gray.shape[1], gray.shape[0])
        return True

    def solve(self) -> CalibResult:
        if len(self.objpoints) < 5 or self.image_size is None:
            return CalibResult(False, 0.0, np.zeros((3, 3), np.float32), np.zeros((5, 1), np.float32), (0, 0))
        K = np.zeros((3, 3), np.float32)
        dist = np.zeros((8, 1), np.float32)
        flags = 0
        rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
            self.objpoints, self.imgpoints, self.image_size, K, dist, flags=flags
        )
        self.collecting = False
        return CalibResult(True, float(rms), K, dist, self.image_size)


_CALIBRATOR: Optional[Calibrator] = None


def get_calibrator() -> Calibrator:
    global _CALIBRATOR
    if _CALIBRATOR is None:
        _CALIBRATOR = Calibrator()
    return _CALIBRATOR


