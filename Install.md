# Sonar Overlay — Installation (Conda, no system Python changes)

These steps create an isolated conda environment named `sonaroverlay` (Python 3.10) and install all dependencies there. Your system and base Python remain untouched.

## 1) Install Conda (Miniforge recommended)
- macOS (Apple Silicon/Intel): download Miniforge from `https://github.com/conda-forge/miniforge`
- Alternatively, Miniconda: `https://docs.conda.io/en/latest/miniconda.html`

After installation, open a new terminal so `conda` is on PATH.

## 2) Create and activate the environment
From the repository root (this directory):

```bash
conda env create -f environment.yml
conda activate sonaroverlay
python -m pip install -r requirements.txt
```

Notes:
- We install core binary libs (OpenCV, snappy, numpy) via conda for reliability on macOS.
- We install the app/server dependencies via pip inside the conda env.

## 3) (Optional) Compile protobuf when the proto is ready
Once the Water Linked `.proto` is in place:

```bash
python -m grpc_tools.protoc -I backend/proto \
  --python_out backend/proto \
  backend/proto/waterlinked_sonar.proto
```

## 4) Run the server (stub for now)

```bash
uvicorn backend.main:app --reload
```

Then open `http://localhost:8000` (the placeholder UI will be added later).

## 5) macOS camera permissions
On first camera access, macOS may prompt for permission. If you don’t see a prompt:
- System Settings → Privacy & Security → Camera → enable access for your terminal/IDE.

## 6) Next steps (will be added in subsequent commits)
- Camera selection and live MJPEG stream
- Calibration (intrinsics) capture and solve
- UDP RIP2 listener and RangeImage decoding
- Point cloud projection using known sonar→camera extrinsics
- Overlay controls in the web UI

## 7) Common issues
- If `cv2` fails to import, ensure the `sonaroverlay` environment is activated and that OpenCV was installed via conda as specified.
- If `python-snappy` errors, ensure the conda package `snappy` was installed by the `environment.yml`. Re-run `conda env update -f environment.yml`.


