"""
NexusMatch - Trust Feature Ablation and Behaviour Trend Experiment.

Purpose:
    Quickly decide whether recent behavioural trends improve the current
    NexusMatch Trust model before Phase 2 is frozen.

Feature sets:
    A. Current 14 features
    B. Core 5 Trust features
    C. Core 5 + 5 trend features
    D. Current 14 + 5 trend features

Trend feature:
    recent_3_rate - historical_rate

Evaluation:
    - Same chronological split used by the main Trust training script.
    - Logistic Regression is used for a controlled feature ablation.
    - Validation Average Precision is the primary feature-set selection metric.
    - Validation threshold is chosen by F1 for the unreliable class.
    - The selected feature set is then calibrated on train+validation and
      evaluated once on the unseen test set.

IMPORTANT:
    The data is synthetic NexusMatch simulation data. Results are for
    development/pipeline validation and must not be reported as real-player
    predictive performance.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "ml"
    / "nexusmatch_future_trust_dataset.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "ml"
    / "trust_ablation_results"
)

TARGET = "future_unreliable_3"
RANDOM_STATE = 42


CORE_FEATURES = [
    "join_success_rate",
    "queue_abandon_rate",
    "completion_rate",
    "disconnect_rate",
    "reconnect_success_rate",
]

CURRENT_FEATURES = [
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

TREND_SOURCE_MAP = {
    "join_success_rate": "recent_3_join_success_rate",
    "queue_abandon_rate": "recent_3_queue_abandon_rate",
    "completion_rate": "recent_3_completion_rate",
    "disconnect_rate": "recent_3_disconnect_rate",
    "reconnect_success_rate": "recent_3_reconnect_success_rate",
}

TREND_FEATURES = [
    "join_success_trend",
    "queue_abandon_trend",
    "completion_trend",
    "disconnect_trend",
    "reconnect_success_trend",
]

TREND_COLUMN_MAP = dict(
    zip(
        TREND_SOURCE_MAP.keys(),
        TREND_FEATURES,
    )
)


def temporal_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Use the same chronological split as the main Trust trainer."""
    dates = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    train_cut = dates.quantile(0.70)
    validation_cut = dates.quantile(0.85)

    future_end = pd.to_datetime(
        df["future_window_end"],
        errors="coerce",
        utc=True,
    )

    train = df[
        (dates <= train_cut)
        & (future_end <= train_cut)
    ].copy()

    validation = df[
        (dates > train_cut)
        & (future_end <= validation_cut)
    ].copy()

    test = df[
        dates > validation_cut
    ].copy()

    return train, validation, test


def choose_threshold(
    y_true: pd.Series,
    probabilities: np.ndarray,
) -> float:
    """Choose threshold that maximizes validation F1."""
    precision, recall, thresholds = precision_recall_curve(
        y_true,
        probabilities,
    )

    if len(thresholds) == 0:
        return 0.50

    f1_values = (
        2
        * precision[:-1]
        * recall[:-1]
        / (
            precision[:-1]
            + recall[:-1]
            + 1e-12
        )
    )

    return float(
        thresholds[int(np.nanargmax(f1_values))]
    )


def evaluate(
    name: str,
    y_true: pd.Series,
    probabilities: np.ndarray,
    threshold: float,
) -> dict:
    predictions = (
        probabilities >= threshold
    ).astype(int)

    return {
        "feature_set": name,
        "threshold": threshold,
        "accuracy": accuracy_score(
            y_true,
            predictions,
        ),
        "balanced_accuracy": balanced_accuracy_score(
            y_true,
            predictions,
        ),
        "precision_unreliable": precision_score(
            y_true,
            predictions,
            zero_division=0,
        ),
        "recall_unreliable": recall_score(
            y_true,
            predictions,
            zero_division=0,
        ),
        "f1_unreliable": f1_score(
            y_true,
            predictions,
            zero_division=0,
        ),
        "roc_auc": roc_auc_score(
            y_true,
            probabilities,
        ),
        "average_precision": average_precision_score(
            y_true,
            probabilities,
        ),
        "brier_score": brier_score_loss(
            y_true,
            probabilities,
        ),
    }


def build_model() -> Pipeline:
    return Pipeline(
        [
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=3000,
                    C=0.5,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def main() -> None:
    print("NexusMatch - Trust Ablation + Trend Experiment")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing dataset: {INPUT_FILE}. "
            "Run prepare_nexusmatch_trust_dataset.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    required = set(CURRENT_FEATURES) | {
        TARGET,
        "player_id",
        "timestamp",
        "future_window_end",
    }

    missing = sorted(
        required.difference(df.columns)
    )

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    # Create recent-vs-history behavioural trend features.
    for historical, trend_name in TREND_COLUMN_MAP.items():
        recent = TREND_SOURCE_MAP[historical]

        df[trend_name] = (
            df[recent] - df[historical]
        )

    all_features = (
        CURRENT_FEATURES
        + TREND_FEATURES
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )
    df["future_window_end"] = pd.to_datetime(
        df["future_window_end"],
        errors="coerce",
        utc=True,
    )

    df = df.dropna(
        subset=all_features
        + [TARGET, "timestamp", "future_window_end"]
    ).copy()

    train, validation, test = temporal_split(df)

    if train.empty or validation.empty or test.empty:
        raise RuntimeError(
            "One or more temporal splits are empty."
        )

    print(f"Total examples     : {len(df):,}")
    print(f"Training examples  : {len(train):,}")
    print(f"Validation examples: {len(validation):,}")
    print(f"Testing examples   : {len(test):,}")

    print(
        f"Train unreliable rate: "
        f"{train[TARGET].mean() * 100:.2f}%"
    )
    print(
        f"Validation unreliable rate: "
        f"{validation[TARGET].mean() * 100:.2f}%"
    )
    print(
        f"Test unreliable rate: "
        f"{test[TARGET].mean() * 100:.2f}%"
    )

    feature_sets = {
        "A_Current_14": CURRENT_FEATURES,
        "B_Core_5": CORE_FEATURES,
        "C_Core_5_Plus_Trend": (
            CORE_FEATURES
            + TREND_FEATURES
        ),
        "D_Current_14_Plus_Trend": all_features,
    }

    y_train = train[TARGET].astype(int)
    y_val = validation[TARGET].astype(int)

    validation_results = []

    print(
        "\n========== VALIDATION ABLATION =========="
    )

    for name, features in feature_sets.items():
        model = build_model()

        model.fit(
            train[features],
            y_train,
        )

        probabilities = model.predict_proba(
            validation[features]
        )[:, 1]

        threshold = choose_threshold(
            y_val,
            probabilities,
        )

        result = evaluate(
            name,
            y_val,
            probabilities,
            threshold,
        )

        result["feature_count"] = len(features)
        validation_results.append(result)

    validation_table = pd.DataFrame(
        validation_results
    ).sort_values(
        [
            "average_precision",
            "roc_auc",
            "f1_unreliable",
        ],
        ascending=False,
    )

    print(
        validation_table.to_string(
            index=False
        )
    )

    best_name = validation_table.iloc[0][
        "feature_set"
    ]
    best_features = feature_sets[best_name]
    best_threshold = float(
        validation_table.iloc[0]["threshold"]
    )

    print(
        f"\nSelected feature set: {best_name}"
    )
    print(
        f"Selected features ({len(best_features)}):"
    )
    for feature in best_features:
        print(f"  - {feature}")

    # Train and calibrate the selected feature set using only
    # train+validation, then evaluate once on the unseen test split.
    combined = pd.concat(
        [
            train,
            validation,
        ],
        ignore_index=True,
    )

    final_model = build_model()

    calibrated_model = CalibratedClassifierCV(
        final_model,
        method="sigmoid",
        cv=3,
    )

    calibrated_model.fit(
        combined[best_features],
        combined[TARGET].astype(int),
    )

    test_probability = (
        calibrated_model.predict_proba(
            test[best_features]
        )[:, 1]
    )

    test_result = evaluate(
        "Selected Feature Set - Calibrated Unseen Test",
        test[TARGET].astype(int),
        test_probability,
        best_threshold,
    )

    print(
        "\n========== SELECTED FEATURE SET - "
        "CALIBRATED UNSEEN TEST =========="
    )
    print(
        pd.DataFrame(
            [test_result]
        ).to_string(index=False)
    )
    print("Confusion matrix:")
    print(
        confusion_matrix(
            test[TARGET].astype(int),
            (
                test_probability
                >= best_threshold
            ).astype(int),
        )
    )

    # Save outputs.
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    validation_file = (
        OUTPUT_DIR
        / "validation_ablation_comparison.csv"
    )

    test_file = (
        OUTPUT_DIR
        / "selected_feature_set_test_metrics.csv"
    )

    prediction_file = (
        OUTPUT_DIR
        / "selected_feature_set_test_predictions.csv"
    )

    model_file = (
        OUTPUT_DIR
        / "selected_trust_model.joblib"
    )

    coefficient_file = (
        OUTPUT_DIR
        / "selected_feature_coefficients.csv"
    )

    validation_table.to_csv(
        validation_file,
        index=False,
    )

    pd.DataFrame(
        [test_result]
    ).to_csv(
        test_file,
        index=False,
    )

    test_output = test[
        [
            "player_id",
            "timestamp",
            TARGET,
        ]
    ].copy()

    test_output["unreliable_risk"] = (
        test_probability
    )

    test_output["trust_score"] = (
        100
        * (
            1
            - test_probability
        )
    )

    test_output["predicted_unreliable"] = (
        test_probability
        >= best_threshold
    ).astype(int)

    test_output.to_csv(
        prediction_file,
        index=False,
    )

    joblib.dump(
        {
            "model": calibrated_model,
            "features": best_features,
            "threshold": best_threshold,
            "target": TARGET,
            "trust_formula": (
                "100 * (1 - predicted_unreliable_risk)"
            ),
            "data_type": "synthetic NexusMatch simulation",
        },
        model_file,
    )

    # Extract coefficients from the base Logistic Regression fitted inside
    # the calibrated classifier. Each calibration fold contains a clone of
    # the model; export the mean coefficient magnitude/direction.
    fold_coefficients = []

    for calibrated_fold in calibrated_model.calibrated_classifiers_:
        estimator = calibrated_fold.estimator
        classifier = estimator.named_steps["model"]
        fold_coefficients.append(
            classifier.coef_[0]
        )

    mean_coefficients = np.mean(
        np.vstack(
            fold_coefficients
        ),
        axis=0,
    )

    coefficient_table = pd.DataFrame(
        {
            "feature": best_features,
            "coefficient": mean_coefficients,
            "absolute_importance": np.abs(
                mean_coefficients
            ),
        }
    ).sort_values(
        "absolute_importance",
        ascending=False,
    )

    coefficient_table.to_csv(
        coefficient_file,
        index=False,
    )

    print(
        "\n========== SELECTED FEATURE COEFFICIENTS =========="
    )
    print(
        coefficient_table.to_string(
            index=False
        )
    )

    print(
        f"\nSaved validation comparison: {validation_file}"
    )
    print(
        f"Saved selected test metrics: {test_file}"
    )
    print(
        f"Saved test predictions: {prediction_file}"
    )
    print(
        f"Saved selected model: {model_file}"
    )
    print(
        f"Saved selected coefficients: {coefficient_file}"
    )

    print(
        "\nNOTE: Results are based on synthetic simulation data "
        "and are for development/pipeline validation only."
    )


if __name__ == "__main__":
    main()
