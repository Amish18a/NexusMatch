"""
NexusMatch - Research-grade Future-Window Trust Model.

Goal:
    Predict whether a player will show a leaver event in at least one of the
    next three matches using only historical information.

Design:
    - chronological train/validation/test split
    - target windows do not cross the relevant split boundary for train/val
    - class-balanced models
    - validation-based threshold selection
    - imbalance-aware metrics
    - comparison with a historical-risk baseline
    - tree feature importance
    - final Trust Risk / Trust Score export

Primary metrics:
    Average Precision (PR-AUC)
    Leaver F1
    Leaver Recall
    ROC-AUC
    Balanced Accuracy

Accuracy is reported but is NOT the primary selection metric.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
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
    / "future_window_trust_dataset.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "ml" / "future_window_results"

FEATURES = [
    "history_matches",
    "prior_leaver_rate",
    "recent_3_leaver_rate",
    "prior_avg_kda_ratio",
    "recent_3_avg_kda_ratio",
    "prior_avg_gold_per_min",
    "recent_3_avg_gold_per_min",
    "prior_avg_xp_per_min",
    "recent_3_avg_xp_per_min",
    "prior_avg_chat_message_count",
    "recent_3_avg_chat_message_count",
    "prior_avg_avg_message_length",
    "recent_3_avg_avg_message_length",
]

TARGET = "future_leaver_3"

RANDOM_STATE = 42


def temporal_split(df: pd.DataFrame):
    """
    Create 70/15/15 chronological splits.

    Training examples are kept only when the complete target window ends inside
    the training period. This prevents training labels from using later data.
    """
    dates = df["start_datetime"].sort_values()

    train_cut = dates.quantile(0.70)
    val_cut = dates.quantile(0.85)

    train = df[
        (df["start_datetime"] <= train_cut)
        & (df["future_window_end"] <= train_cut)
    ].copy()

    validation = df[
        (df["start_datetime"] > train_cut)
        & (df["future_window_end"] <= val_cut)
    ].copy()

    test = df[
        (df["start_datetime"] > val_cut)
    ].copy()

    return train, validation, test


def choose_threshold(y_true, probabilities):
    """
    Select a classification threshold using validation F1 for the positive
    leaver class instead of forcing a threshold of 0.50.
    """
    precision, recall, thresholds = precision_recall_curve(
        y_true,
        probabilities,
    )

    if len(thresholds) == 0:
        return 0.50

    f1_values = (
        2 * precision[:-1] * recall[:-1]
        / (precision[:-1] + recall[:-1] + 1e-12)
    )

    return float(thresholds[int(np.nanargmax(f1_values))])


def evaluate(
    name,
    y_true,
    probabilities,
    threshold,
):
    predictions = (probabilities >= threshold).astype(int)

    return {
        "model": name,
        "threshold": threshold,
        "accuracy": accuracy_score(y_true, predictions),
        "balanced_accuracy": balanced_accuracy_score(
            y_true, predictions
        ),
        "precision_leaver": precision_score(
            y_true, predictions, zero_division=0
        ),
        "recall_leaver": recall_score(
            y_true, predictions, zero_division=0
        ),
        "f1_leaver": f1_score(
            y_true, predictions, zero_division=0
        ),
        "roc_auc": roc_auc_score(y_true, probabilities),
        "average_precision": average_precision_score(
            y_true, probabilities
        ),
    }


def print_evaluation(
    name,
    y_true,
    probabilities,
    threshold,
):
    result = evaluate(
        name,
        y_true,
        probabilities,
        threshold,
    )

    predictions = (probabilities >= threshold).astype(int)

    print(f"\n========== {name.upper()} ==========")
    print(pd.DataFrame([result]).to_string(index=False))
    print("Confusion matrix:")
    print(confusion_matrix(y_true, predictions))

    return result


def main() -> None:
    print("NexusMatch - Future-Window Trust Model")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing dataset: {INPUT_FILE}. "
            "Run prepare_future_window_dataset.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    required = set(FEATURES) | {
        TARGET,
        "account_id",
        "start_datetime",
        "future_window_end",
    }

    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["start_datetime"] = pd.to_datetime(
        df["start_datetime"],
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
        + [TARGET, "start_datetime", "future_window_end"]
    ).copy()

    train, validation, test = temporal_split(df)

    if train.empty or validation.empty or test.empty:
        raise RuntimeError(
            "Temporal split produced an empty dataset. "
            "Inspect the date distribution."
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
            f"{name} positive rate: "
            f"{frame[TARGET].mean() * 100:.2f}%"
        )
        print(
            f"{name} unique players: "
            f"{frame['account_id'].nunique():,}"
        )

    X_train = train[FEATURES]
    y_train = train[TARGET].astype(int)

    X_val = validation[FEATURES]
    y_val = validation[TARGET].astype(int)

    X_test = test[FEATURES]
    y_test = test[TARGET].astype(int)

    models = {
        "Logistic Regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=5000,
                        C=0.5,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=12,
            min_samples_leaf=10,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=500,
            max_depth=12,
            min_samples_leaf=10,
            max_features="sqrt",
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }

    validation_results = []
    fitted_models = {}

    baseline_prob = validation["prior_leaver_rate"].to_numpy()
    baseline_threshold = choose_threshold(
        y_val,
        baseline_prob,
    )

    validation_results.append(
        print_evaluation(
            "Historical Leaver Rate Baseline",
            y_val,
            baseline_prob,
            baseline_threshold,
        )
    )

    for name, model in models.items():
        model.fit(X_train, y_train)

        probabilities = model.predict_proba(X_val)[:, 1]
        threshold = choose_threshold(
            y_val,
            probabilities,
        )

        result = print_evaluation(
            name,
            y_val,
            probabilities,
            threshold,
        )

        validation_results.append(result)
        fitted_models[name] = model

    validation_table = (
        pd.DataFrame(validation_results)
        .sort_values(
            ["average_precision", "f1_leaver"],
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print("\n========== VALIDATION COMPARISON ==========")
    print(validation_table.to_string(index=False))

    best_name = validation_table.iloc[0]["model"]

    if best_name == "Historical Leaver Rate Baseline":
        raise RuntimeError(
            "No ML model beat the historical baseline on validation. "
            "Do not promote an ML model yet."
        )

    best_threshold = float(
        validation_table.iloc[0]["threshold"]
    )

    print(f"\nSelected model: {best_name}")
    print(f"Selected threshold: {best_threshold:.6f}")

    train_plus_validation = pd.concat(
        [train, validation],
        ignore_index=True,
    )

    final_model = models[best_name]
    final_model.fit(
        train_plus_validation[FEATURES],
        train_plus_validation[TARGET].astype(int),
    )

    test_probabilities = final_model.predict_proba(
        X_test
    )[:, 1]

    test_result = print_evaluation(
        f"{best_name} - Unseen Test",
        y_test,
        test_probabilities,
        best_threshold,
    )

    test_output = test[
        [
            "account_id",
            "match_id",
            "start_datetime",
            "history_matches",
            "prior_leaver_rate",
            TARGET,
        ]
    ].copy()

    test_output["predicted_leaver_risk"] = test_probabilities
    test_output["trust_score"] = (
        100 * (1 - test_output["predicted_leaver_risk"])
    ).clip(0, 100)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    validation_file = OUTPUT_DIR / "validation_model_comparison.csv"
    validation_table.to_csv(
        validation_file,
        index=False,
    )

    test_file = OUTPUT_DIR / "final_test_metrics.csv"
    pd.DataFrame([test_result]).to_csv(
        test_file,
        index=False,
    )

    predictions_file = (
        OUTPUT_DIR / "test_trust_predictions.csv"
    )
    test_output.to_csv(
        predictions_file,
        index=False,
    )

    if hasattr(final_model, "feature_importances_"):
        importance = pd.Series(
            final_model.feature_importances_,
            index=FEATURES,
            name="importance",
        ).sort_values(ascending=False)

        importance_file = (
            OUTPUT_DIR / "final_tree_feature_importance.csv"
        )

        importance.to_csv(
            importance_file,
            header=True,
        )

        print("\n========== FINAL FEATURE IMPORTANCE ==========")
        print(importance.to_string())
        print(f"Saved: {importance_file}")

    model_file = OUTPUT_DIR / "final_trust_model.joblib"

    package = {
        "model": final_model,
        "features": FEATURES,
        "threshold": best_threshold,
        "target": TARGET,
        "trust_score_formula": "100 * (1 - predicted_leaver_risk)",
    }

    joblib.dump(
        package,
        model_file,
    )

    print("\n========== FINAL TEST RESULT ==========")
    print(pd.DataFrame([test_result]).to_string(index=False))

    print(f"Saved validation comparison: {validation_file}")
    print(f"Saved final test metrics    : {test_file}")
    print(f"Saved test trust scores     : {predictions_file}")
    print(f"Saved model package         : {model_file}")


if __name__ == "__main__":
    main()
