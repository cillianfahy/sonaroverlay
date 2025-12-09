# sonaroverlay

Sonar Overlay web app (FastAPI + OpenCV) that overlays Water Linked 3D-15 sonar points on a live camera stream.

## Setup
Follow Install.md for a clean conda install (environment `sonaroverlay`, Python 3.10). This avoids modifying system or base Python.

## Run
```bash
conda activate sonaroverlay
uvicorn backend.main:app --reload
```
Open `http://localhost:8000`.

## Usage
1. Pick a camera in the UI and click Select.
2. Calibration:
   - Enter checkerboard rows, cols, and square size (meters).
   - Click Start, point the board at the camera in multiple poses, click Capture each time (aim for 15–25 samples).
   - Click Solve. This stores intrinsics on disk and activates projection.
3. Extrinsics:
   - Enter sonar→camera pose (rvec Rodrigues, tvec meters) and Save.
4. Sonar:
   - Default multicast `224.0.0.96:4747` is enabled. If the proto is present, RIP2 is decoded and points are projected.
5. Overlay:
   - Toggle on/off, adjust point size and decimation.

## Notes
- If RIP2 proto is not compiled, the app will still run (no points until compiled).
- To compile the proto automatically, ensure `grpcio-tools` is installed (it is in requirements.txt). On first packet, the app tries to compile `backend/proto/waterlinked_sonar.proto` if needed.
- macOS camera permissions are required for the stream to work.

