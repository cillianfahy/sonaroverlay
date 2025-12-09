from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
import numpy as np


class CameraSelectRequest(BaseModel):
    device_index: int = Field(..., ge=0)


class CalibStartRequest(BaseModel):
    rows: int = Field(..., ge=3)
    cols: int = Field(..., ge=3)
    square_size_m: float = Field(..., gt=0)


class CalibStatusResponse(BaseModel):
    collecting: bool
    num_samples: int
    target_rows: int
    target_cols: int
    square_size_m: float


class CalibSolveResponse(BaseModel):
    ok: bool
    rms_error: float


class ExtrinsicsModel(BaseModel):
    # Rotation as Rodrigues vector (rvec) and translation t (meters), sonar->camera
    rvec: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    tvec: Tuple[float, float, float] = (0.0, 0.0, 0.0)


class OverlayOptionsModel(BaseModel):
    enabled: bool = True
    point_size: int = Field(2, ge=1, le=10)
    decimate: int = Field(4, ge=1, le=32)
    color_mode: str = Field("range", pattern="^(range|intensity)$")
    z_min_m: float = -100.0
    z_max_m: float = 100.0


class SonarConfigModel(BaseModel):
    multicast_addr: str = "224.0.0.96"
    port: int = 4747
    enabled: bool = True


