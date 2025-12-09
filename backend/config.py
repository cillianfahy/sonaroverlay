import json
import os
from typing import Any, Dict, Tuple
import numpy as np
from .models import ExtrinsicsModel, OverlayOptionsModel

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage"))
INTRINSICS_PATH = os.path.join(STORAGE_DIR, "camera_intrinsics.json")
EXTRINSICS_PATH = os.path.join(STORAGE_DIR, "extrinsics.json")
OVERLAY_PATH = os.path.join(STORAGE_DIR, "overlay_options.json")


def _save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_camera_intrinsics(K: np.ndarray, dist: np.ndarray, image_size: Tuple[int, int]) -> None:
    data = {
        "K": K.tolist(),
        "dist": dist.flatten().tolist(),
        "image_size": list(image_size),
    }
    _save_json(INTRINSICS_PATH, data)


def load_camera_intrinsics():
    data = _load_json(INTRINSICS_PATH)
    if not data:
        return None, None, None
    K = np.array(data["K"], dtype=np.float32)
    dist = np.array(data["dist"], dtype=np.float32)
    image_size = tuple(data["image_size"])
    return K, dist, image_size


def save_extrinsics(model: ExtrinsicsModel) -> None:
    _save_json(EXTRINSICS_PATH, {"rvec": list(model.rvec), "tvec": list(model.tvec)})


def load_extrinsics() -> ExtrinsicsModel:
    data = _load_json(EXTRINSICS_PATH)
    if not data:
        return ExtrinsicsModel()
    return ExtrinsicsModel(rvec=tuple(data.get("rvec", (0.0, 0.0, 0.0))),
                           tvec=tuple(data.get("tvec", (0.0, 0.0, 0.0))))


def save_overlay_options(model: OverlayOptionsModel) -> None:
    _save_json(OVERLAY_PATH, model.model_dump())


def load_overlay_options() -> OverlayOptionsModel:
    data = _load_json(OVERLAY_PATH)
    if not data:
        return OverlayOptionsModel()
    return OverlayOptionsModel(**data)


