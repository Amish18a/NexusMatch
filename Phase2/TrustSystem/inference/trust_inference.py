"""
NexusMatch - Trust Model Inference Bridge.

Loads the calibrated Trust model produced by:
    ml/train_nexusmatch_trust_models.py

Exposes predict_trust(features) for Python/server integration and a
command-line interface for the future C++ bridge.

The CLI prints one machine-readable line:
    risk=<float> trust=<float> label=<reliable|unreliable>

The current model is trained on synthetic NexusMatch simulation data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping

import joblib
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = (
    BASE_DIR
    / "data"
    / "ml"
    / "nexusmatch_trust_results"
    / "final_trust_model.joblib"
)

FEATURES = [
    "history_sessions",
    "join_success_rate",
    "queue_abandon_rate",
    "completion_rate",
    "disconnect_rate",
    "reconnect_success_rate",
    "recent_3_join_success_rate",
    "recent_3_queue_abandon_rate",
    "recent_3_completion_rate",
    "recent_3_disconnect_rate",
    "recent_3_reconnect_success_rate",
    "avg_wait_time_sec",
    "avg_ping_ms",
    "avg_chat_messages",
]


def load_model(model_path: str | Path = DEFAULT_MODEL) -> dict:
    """Load and validate the saved NexusMatch model package."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Trust model not found: {path}. Run the training script first."
        )
    package = joblib.load(path)
    required_keys = {"model", "features", "threshold"}
    missing = sorted(required_keys.difference(package))
    if missing:
        raise ValueError(f"Invalid model package. Missing keys: {missing}")
    if list(package["features"]) != FEATURES:
        raise ValueError(
            "Model feature order does not match the NexusMatch Trust schema."
        )
    return package


def validate_features(features: Mapping[str, float]) -> None:
    """Validate a single player Trust feature vector."""
    missing = [f for f in FEATURES if f not in features]
    if missing:
        raise ValueError(f"Missing Trust features: {missing}")
    for feature in FEATURES:
        value = float(features[feature])
        if not np.isfinite(value):
            raise ValueError(f"Feature {feature!r} must be finite.")

    rate_features = [
        "join_success_rate", "queue_abandon_rate", "completion_rate",
        "disconnect_rate", "reconnect_success_rate",
        "recent_3_join_success_rate", "recent_3_queue_abandon_rate",
        "recent_3_completion_rate", "recent_3_disconnect_rate",
        "recent_3_reconnect_success_rate",
    ]
    for feature in rate_features:
        value = float(features[feature])
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Feature {feature!r} must be between 0 and 1.")

    nonnegative = [
        "history_sessions", "avg_wait_time_sec",
        "avg_ping_ms", "avg_chat_messages",
    ]
    for feature in nonnegative:
        if float(features[feature]) < 0:
            raise ValueError(f"Feature {feature!r} cannot be negative.")


def predict_trust(
    features: Mapping[str, float],
    model_path: str | Path = DEFAULT_MODEL,
) -> dict:
    """Return unreliable risk, Trust Score, label, and threshold."""
    validate_features(features)
    package = load_model(model_path)
    ordered_values = [float(features[f]) for f in package["features"]]
    probability = float(
        package["model"].predict_proba(
            np.asarray([ordered_values], dtype=float)
        )[0, 1]
    )
    probability = float(np.clip(probability, 0.0, 1.0))
    trust_score = float(np.clip(100.0 * (1.0 - probability), 0.0, 100.0))
    threshold = float(package["threshold"])
    label = "unreliable" if probability >= threshold else "reliable"
    return {
        "unreliable_risk": probability,
        "trust_score": trust_score,
        "trust_label": label,
        "threshold": threshold,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run NexusMatch Trust inference for one player."
    )
    parser.add_argument(
        "--model", default=str(DEFAULT_MODEL), help="Path to final_trust_model.joblib"
    )
    for feature in FEATURES:
        parser.add_argument(f"--{feature}", type=float, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    values = {feature: getattr(args, feature) for feature in FEATURES}
    result = predict_trust(values, args.model)
    print(
        "risk={risk:.6f} trust={trust:.2f} label={label} threshold={threshold:.6f}".format(
            risk=result["unreliable_risk"],
            trust=result["trust_score"],
            label=result["trust_label"],
            threshold=result["threshold"],
        )
    )


if __name__ == "__main__":
    main()
