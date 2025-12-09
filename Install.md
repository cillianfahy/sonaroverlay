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
# Avoid mixing with user site-packages
export PYTHONNOUSERSITE=1
python -m pip install -r requirements.txt
```

Notes:
- We install core binary libs via conda-forge for macOS reliability:
  - `snappy` (C++ lib), `python-snappy` (Python binding), `protobuf` (runtime)
- We install the app/server dependencies via pip inside the conda env (e.g., `grpcio-tools`).
- Do NOT `pip install snappy` (that is SnapPy, unrelated). Use `python-snappy` which is already provided via conda in `environment.yml`.

## 3) (Optional) Compile protobuf when the proto is ready
Once the Water Linked `.proto` is in place:

```bash
python -m grpc_tools.protoc -I backend/proto \
  --python_out backend/proto \
  backend/proto/waterlinked_sonar.proto
```

Sanity checks:
```bash
python - <<'PY'
import sys; print("python:", sys.executable)
import snappy; print("snappy ok, has decompress:", hasattr(snappy, "decompress"))
from google.protobuf.any_pb2 import Any; print("protobuf Any import ok")
import importlib
try:
    wl = importlib.import_module("backend.proto.waterlinked_sonar_pb2")
    print("generated proto import ok:", wl.__name__)
except Exception as e:
    print("generated proto import failed:", e)
PY
```

## 4) Run the server (stub for now)

```bash
uvicorn backend.main:app --reload
```

Then open `http://localhost:8000` (the placeholder UI will be added later).

## 5) macOS camera permissions
On first camera access, macOS may prompt for permission. If you don’t see a prompt:
- System Settings → Privacy & Security → Camera → enable access for your terminal/IDE.

## 6) Troubleshooting checklist
- Am I using the env’s Python?
  - `which python` → should point to the conda env `.../envs/sonaroverlay/bin/python`
  - Prefer `python -m pip ...` to guarantee same interpreter.
- Imports still fail?
  - `export PYTHONNOUSERSITE=1` to avoid mixing user site-packages.
  - `python -c "import snappy, google.protobuf; print('ok')"`
- `snappy` import seems wrong package?
  - `python -c "import snappy, inspect; print(snappy.__file__)"`
  - If it points to SnapPy, remove it: `python -m pip uninstall -y snappy`
  - Ensure `python-snappy` is installed (provided by conda in `environment.yml`)
- `ModuleNotFoundError: No module named 'google'`
  - Ensure `protobuf` is installed in the env (provided by conda in `environment.yml`)
- Generated proto missing
  - Re-run the `grpc_tools.protoc` command above; output must land under `backend/proto/`
  - That directory is a Python package (`__init__.py`), so imports work.

## 6) Next steps (will be added in subsequent commits)
- Camera selection and live MJPEG stream
- Calibration (intrinsics) capture and solve
- UDP RIP2 listener and RangeImage decoding
- Point cloud projection using known sonar→camera extrinsics
- Overlay controls in the web UI

## 7) Common issues
- If `cv2` fails to import, ensure the `sonaroverlay` environment is activated and that OpenCV was installed via conda as specified.
- If `python-snappy` errors, ensure the conda package `snappy` was installed by the `environment.yml`. Re-run `conda env update -f environment.yml`.


