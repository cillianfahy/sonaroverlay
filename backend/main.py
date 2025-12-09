from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .models import (
    CameraSelectRequest,
    CalibStartRequest,
    CalibStatusResponse,
    CalibSolveResponse,
    ExtrinsicsModel,
    OverlayOptionsModel,
    SonarConfigModel,
)
from . import camera
from . import calibration
from . import config
from . import sonar_rip2
from . import projector
import os

app = FastAPI(title="Sonar Overlay", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
def on_startup():
    os.makedirs(config.STORAGE_DIR, exist_ok=True)
    # Start camera and sonar managers
    camera.get_camera_manager()
    sonar_rip2.get_sonar_manager()

@app.get("/")
def index():
    frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"))
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Frontend not found"}

# Camera endpoints
@app.get("/api/cameras")
def list_cameras():
    return {"devices": camera.enumerate_cameras()}

@app.post("/api/camera/select")
def select_camera(req: CameraSelectRequest):
    ok = camera.get_camera_manager().select_device(req.device_index)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to open camera")
    return {"ok": True, "device_index": req.device_index}

@app.get("/stream.mjpg")
def stream_mjpg():
    def frame_generator():
        while True:
            frame = camera.get_camera_manager().get_frame_with_overlay()
            if frame is None:
                continue
            # Encode JPEG
            import cv2
            import numpy as np
            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            jpg_bytes = buf.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n")
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame", headers=headers)

# Calibration endpoints
@app.post("/api/calib/start", response_model=CalibStatusResponse)
def calib_start(req: CalibStartRequest):
    calibration.get_calibrator().start(req.rows, req.cols, req.square_size_m)
    return calibration.get_calibrator().status()

@app.post("/api/calib/capture", response_model=CalibStatusResponse)
def calib_capture():
    frame = camera.get_camera_manager().get_frame_raw()
    if frame is None:
        raise HTTPException(status_code=400, detail="No frame available")
    ok = calibration.get_calibrator().capture(frame)
    if not ok:
        raise HTTPException(status_code=400, detail="Chessboard not found")
    return calibration.get_calibrator().status()

@app.post("/api/calib/solve", response_model=CalibSolveResponse)
def calib_solve():
    result = calibration.get_calibrator().solve()
    if not result.ok:
        raise HTTPException(status_code=400, detail="Calibration failed")
    config.save_camera_intrinsics(result.camera_matrix, result.dist_coeffs, result.image_size)
    projector.get_projector().set_intrinsics(result.camera_matrix, result.dist_coeffs, result.image_size)
    return CalibSolveResponse(ok=True, rms_error=result.rms_error)

@app.get("/api/calib/status", response_model=CalibStatusResponse)
def calib_status():
    return calibration.get_calibrator().status()

# Extrinsics and overlay
@app.get("/api/extrinsics", response_model=ExtrinsicsModel)
def get_extrinsics():
    return config.load_extrinsics()

@app.put("/api/extrinsics")
def put_extrinsics(model: ExtrinsicsModel):
    config.save_extrinsics(model)
    projector.get_projector().set_extrinsics(model)
    return {"ok": True}

@app.get("/api/overlay", response_model=OverlayOptionsModel)
def get_overlay():
    return config.load_overlay_options()

@app.put("/api/overlay")
def put_overlay(model: OverlayOptionsModel):
    config.save_overlay_options(model)
    projector.get_projector().set_overlay_options(model)
    return {"ok": True}

# Sonar config
@app.get("/api/sonar", response_model=SonarConfigModel)
def get_sonar():
    return sonar_rip2.get_sonar_manager().get_config()

@app.put("/api/sonar")
def put_sonar(cfg: SonarConfigModel):
    sonar_rip2.get_sonar_manager().apply_config(cfg)
    return {"ok": True}

@app.get("/api/sonar/stats")
def sonar_stats():
    return sonar_rip2.get_sonar_manager().get_stats()


