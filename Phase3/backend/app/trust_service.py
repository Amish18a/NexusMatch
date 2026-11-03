from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .config import MODEL_PATH, TRUST_INFERENCE_DIR


_MODULE_PATH = TRUST_INFERENCE_DIR / "trust_inference.py"
_SPEC = importlib.util.spec_from_file_location("nexusmatch_trust_inference", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load Trust inference module from {_MODULE_PATH}")
_TRUST_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TRUST_MODULE)


def predict_profile_trust(features: dict[str, float]) -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Saved Trust model is missing: {MODEL_PATH}")
    result = _TRUST_MODULE.predict_trust(features, model_path=MODEL_PATH)
    return {
        "unreliable_risk": float(result["unreliable_risk"]),
        "trust_score": round(float(result["trust_score"]), 2),
        "trust_label": str(result["trust_label"]),
        "threshold": float(result["threshold"]),
    }
