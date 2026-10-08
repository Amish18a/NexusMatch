"""
NexusMatch - Train the project-specific Trust models.

Dataset:
    data/ml/nexusmatch_future_trust_dataset.csv

Target:
    future_unreliable_3 = 1 if at least one of the next three sessions contains
    unreliable behaviour.

Evaluation:
    - chronological train/validation/test split
    - Average Precision and ROC-AUC for ranking
    - leaver/unreliable F1, precision and recall
    - balanced accuracy
    - Brier score for probability quality
    - validation threshold selection

Models:
    - Historical risk baseline
    - Logistic Regression
    - Random Forest
    - Extra Trees
    - Gradient Boosting

The selected model is calibrated on the training+validation data before being
used to generate the final Trust Score:

    Trust Score = 100 * (1 - calibrated predicted unreliable risk)

This is synthetic development data. Report results as simulation results until
the real NexusMatch server/Docker telemetry replaces it.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
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
    / "nexusmatch_trust_results"
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

TARGET = "future_unreliable_3"

RANDOM_STATE = 42


def temporal_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create leakage-aware chronological train/validation/test splits."""
    dates = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    train_cut = dates.quantile(0.70)
    validation_cut = dates.quantile(0.85)

    train = df[
        (dates <= train_cut)
        & (
            pd.to_datetime(
                df["future_window_end"],
                errors="coerce",
                utc=True,
            )
            <= train_cut
        )
    ].copy()

    validation = df[
        (dates > train_cut)
        & (
            pd.to_datetime(
                df["future_window_end"],
                errors="coerce",
                utc=True,
            )
            <= validation_cut
        )
    ].copy()

    test = df[dates > validation_cut].copy()

    return train, validation, test


def choose_threshold(
    y_true: pd.Series,
    probabilities: np.ndarray,
) -> float:
    """Choose a positive-class threshold that maximizes validation F1."""
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
        / (precision[:-1] + recall[:-1] + 1e-12)
    )

    return float(
        thresholds[int(np.nanargmax(f1_values))]
    )


def evaluate_model(
    name: str,
    y_true: pd.Series,
    probabilities: np.ndarray,
    threshold: float,
) -> dict:
    predictions = (probabilities >= threshold).astype(int)

    return {
        "model": name,
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


def print_metrics(
    name: str,
    y_true: pd.Series,
    probabilities: np.ndarray,
    threshold: float,
) -> dict:
    result = evaluate_model(
        name,
        y_true,
        probabilities,
        threshold,
    )

    predictions = (probabilities >= threshold).astype(int)

    print(f"\n========== {name.upper()} ==========")
    print(
        pd.DataFrame([result]).to_string(
            index=False
        )
    )
    print("Confusion matrix:")
    print(
        confusion_matrix(
            y_true,
            predictions,
        )
    )

    return result


def main() -> None:
    print("NexusMatch - Project Trust Model Training")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing dataset: {INPUT_FILE}. "
            "Run prepare_nexusmatch_trust_dataset.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    required = set(FEATURES) | {
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
        subset=FEATURES
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

    for name, frame in [
        ("Train", train),
        ("Validation", validation),
        ("Test", test),
    ]:
        print(
            f"{name} unreliable rate: "
            f"{frame[TARGET].mean() * 100:.2f}%"
        )
        print(
            f"{name} unique players: "
            f"{frame['player_id'].nunique():,}"
        )

    X_train = train[FEATURES]
    y_train = train[TARGET].astype(int)

    X_val = validation[FEATURES]
    y_val = validation[TARGET].astype(int)

    X_test = test[FEATURES]
    y_test = test[TARGET].astype(int)

    # Baseline: historical session-level unreliable rate.
    baseline_prob = validation[
        "queue_abandon_rate"
    ].to_numpy() * 0.20

    baseline_prob += (
        validation["disconnect_rate"].to_numpy()
        * 0.40
    )
    baseline_prob += (
        (1 - validation["completion_rate"].to_numpy())
        * 0.30
    )
    baseline_prob += (
        (1 - validation["join_success_rate"].to_numpy())
        * 0.10
    )
    baseline_prob = np.clip(
        baseline_prob,
        0,
        1,
    )

    baseline_threshold = choose_threshold(
        y_val,
        baseline_prob,
    )

    validation_results = [
        print_metrics(
            "Behavioural Baseline",
            y_val,
            baseline_prob,
            baseline_threshold,
        )
    ]

    models = {
        "Logistic Regression": Pipeline(
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
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            max_depth=12,
            min_samples_leaf=10,
            max_features="sqrt",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=400,
            max_depth=12,
            min_samples_leaf=10,
            max_features="sqrt",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=250,
            learning_rate=0.05,
            max_depth=3,
            min_samples_leaf=10,
            random_state=RANDOM_STATE,
        ),
    }

    fitted = {}

    for name, model in models.items():
        model.fit(
            X_train,
            y_train,
        )

        validation_probability = (
            model.predict_proba(X_val)[:, 1]
        )

        threshold = choose_threshold(
            y_val,
            validation_probability,
        )

        validation_results.append(
            print_metrics(
                name,
                y_val,
                validation_probability,
                threshold,
            )
        )

        fitted[name] = model

    validation_table = (
        pd.DataFrame(validation_results)
        .sort_values(
            ["average_precision", "f1_unreliable"],
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print(
        "\n========== VALIDATION COMPARISON =========="
    )
    print(
        validation_table.to_string(
            index=False
        )
    )

    # Do not select the baseline as the deployable ML model.
    ml_table = validation_table[
        validation_table["model"]
        != "Behavioural Baseline"
    ]

    best_name = ml_table.iloc[0]["model"]
    best_threshold = float(
        ml_table.iloc[0]["threshold"]
    )

    print(f"\nSelected ML model: {best_name}")
    print(
        f"Selected threshold: "
        f"{best_threshold:.6f}"
    )

    # Fit the selected model on train + validation before the final test.
    development = pd.concat(
        [train, validation],
        ignore_index=True,
    )

    selected_base = models[best_name]

    selected_base.fit(
        development[FEATURES],
        development[TARGET].astype(int),
    )

    # Calibrate probabilities using cross-validation within the development
    # data. Test remains untouched until evaluation.
    calibrated = CalibratedClassifierCV(
        estimator=selected_base,
        method="sigmoid",
        cv=3,
        n_jobs=-1,
    )

    calibrated.fit(
        development[FEATURES],
        development[TARGET].astype(int),
    )

    test_probability = calibrated.predict_proba(
        X_test
    )[:, 1]

    test_result = print_metrics(
        f"{best_name} - Calibrated Unseen Test",
        y_test,
        test_probability,
        best_threshold,
    )

    test_output = test[
        [
            "player_id",
            "timestamp",
            "history_sessions",
            "prior_leaver_rate"
            if "prior_leaver_rate" in test.columns
            else "queue_abandon_rate",
            TARGET,
        ]
    ].copy()

    test_output["predicted_unreliable_risk"] = (
        test_probability
    )

    test_output["trust_score"] = (
        100
        * (1 - test_output["predicted_unreliable_risk"])
    ).clip(0, 100)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    validation_file = (
        OUTPUT_DIR
        / "validation_model_comparison.csv"
    )
    validation_table.to_csv(
        validation_file,
        index=False,
    )

    test_metrics_file = (
        OUTPUT_DIR
        / "final_test_metrics.csv"
    )
    pd.DataFrame([test_result]).to_csv(
        test_metrics_file,
        index=False,
    )

    predictions_file = (
        OUTPUT_DIR
        / "test_trust_predictions.csv"
    )
    test_output.to_csv(
        predictions_file,
        index=False,
    )

    # Feature importance is available for tree ensembles.
    importance_model = fitted.get(
        best_name
    )

    if hasattr(
        importance_model,
        "feature_importances_",
    ):
        importance = pd.Series(
            importance_model.feature_importances_,
            index=FEATURES,
            name="importance",
        ).sort_values(
            ascending=False
        )

        importance_file = (
            OUTPUT_DIR
            / "final_feature_importance.csv"
        )

        importance.to_csv(
            importance_file,
            header=True,
        )

        print(
            "\n========== FEATURE IMPORTANCE =========="
        )
        print(
            importance.to_string()
        )
        print(
            f"Saved: {importance_file}"
        )

    model_file = (
        OUTPUT_DIR
        / "final_trust_model.joblib"
    )

    package = {
        "model": calibrated,
        "features": FEATURES,
        "threshold": best_threshold,
        "target": TARGET,
        "trust_score_formula": (
            "100 * (1 - predicted_unreliable_risk)"
        ),
    }

    joblib.dump(
        package,
        model_file,
    )

    print(
        "\n========== FINAL TEST RESULT =========="
    )
    print(
        pd.DataFrame([test_result]).to_string(
            index=False
        )
    )

    print(
        f"Saved validation comparison: {validation_file}"
    )
    print(
        f"Saved final test metrics: {test_metrics_file}"
    )
    print(
        f"Saved test trust predictions: {predictions_file}"
    )
    print(
        f"Saved model package: {model_file}"
    )


if __name__ == "__main__":
    main()
