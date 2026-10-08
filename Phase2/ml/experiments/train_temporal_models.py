"""
NexusMatch - Train temporal Trust baselines.

This experiment predicts whether a player will be recorded as a leaver in the
NEXT observed match, using only their prior match history.

A StratifiedGroupKFold split keeps all observations from a player in either the
training or test fold, reducing player-level leakage.

Models:
    - Logistic Regression
    - Decision Tree
    - Random Forest

Metrics:
    - Accuracy
    - Balanced Accuracy
    - Precision/Recall/F1 for the leaver class
    - ROC-AUC
    - Average Precision (PR-AUC)

A majority-class baseline is also reported.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE_DIR / "data" / "ml" / "temporal_trust_dataset.csv"
OUTPUT_DIR = BASE_DIR / "data" / "ml" / "temporal_results"

FEATURES = [
    "history_matches",
    "prior_leaver_rate",
    "prior_avg_kda_ratio",
    "prior_avg_gold_per_min",
    "prior_avg_xp_per_min",
    "prior_avg_chat_message_count",
    "prior_avg_avg_message_length",
]

TARGET = "leaver_next_match"
GROUP = "account_id"
RANDOM_STATE = 42


def evaluate_model(
    name: str,
    model,
    X_train,
    X_test,
    y_train,
    y_test,
) -> tuple[dict, object]:
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    result = {
        "model": name,
        "accuracy": accuracy_score(y_test, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_test, y_pred),
        "precision_leaver": precision_score(
            y_test, y_pred, pos_label=1, zero_division=0
        ),
        "recall_leaver": recall_score(
            y_test, y_pred, pos_label=1, zero_division=0
        ),
        "f1_leaver": f1_score(
            y_test, y_pred, pos_label=1, zero_division=0
        ),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "average_precision": average_precision_score(y_test, y_prob),
    }

    print(f"\n========== {name.upper()} ==========")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    return result, model


def main() -> None:
    print("NexusMatch - Temporal Trust Model Training")
    print("=" * 56)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Temporal dataset not found. Run prepare_temporal_dataset.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    required = set(FEATURES) | {TARGET, GROUP}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    X = df[FEATURES]
    y = df[TARGET].astype(int)
    groups = df[GROUP]

    splitter = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    train_idx, test_idx = next(
        splitter.split(X, y, groups=groups)
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]
    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    print(f"Training rows: {len(X_train):,}")
    print(f"Testing rows : {len(X_test):,}")
    print(f"Train leaver rate: {y_train.mean():.4f}")
    print(f"Test leaver rate : {y_test.mean():.4f}")

    # Majority-class baseline.
    majority_class = int(y_train.mode().iloc[0])
    majority_pred = np.full(len(y_test), majority_class)

    baseline = {
        "model": "Majority Baseline",
        "accuracy": accuracy_score(y_test, majority_pred),
        "balanced_accuracy": balanced_accuracy_score(
            y_test, majority_pred
        ),
        "precision_leaver": precision_score(
            y_test, majority_pred, pos_label=1, zero_division=0
        ),
        "recall_leaver": recall_score(
            y_test, majority_pred, pos_label=1, zero_division=0
        ),
        "f1_leaver": f1_score(
            y_test, majority_pred, pos_label=1, zero_division=0
        ),
        "roc_auc": float("nan"),
        "average_precision": float("nan"),
    }

    print("\n========== MAJORITY BASELINE ==========")
    print(
        classification_report(
            y_test,
            majority_pred,
            zero_division=0,
        )
    )
    print("Confusion matrix:")
    print(confusion_matrix(y_test, majority_pred))

    models = {
        "Logistic Regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=2000,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "Decision Tree": DecisionTreeClassifier(
            class_weight="balanced",
            max_depth=5,
            min_samples_leaf=20,
            random_state=RANDOM_STATE,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }

    results = [baseline]
    fitted_models = {}

    for name, model in models.items():
        result, fitted = evaluate_model(
            name,
            model,
            X_train,
            X_test,
            y_train,
            y_test,
        )
        results.append(result)
        fitted_models[name] = fitted

    comparison = (
        pd.DataFrame(results)
        .sort_values("f1_leaver", ascending=False)
        .reset_index(drop=True)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    comparison_file = OUTPUT_DIR / "temporal_model_comparison.csv"
    comparison.to_csv(comparison_file, index=False)

    print("\n========== MODEL COMPARISON ==========")
    print(comparison.to_string(index=False))
    print(f"\nSaved comparison: {comparison_file}")

    forest = fitted_models["Random Forest"]

    importances = pd.Series(
        forest.feature_importances_,
        index=FEATURES,
        name="importance",
    ).sort_values(ascending=False)

    importance_file = (
        OUTPUT_DIR / "temporal_random_forest_feature_importance.csv"
    )
    importances.to_csv(importance_file, header=True)

    print("\n========== RANDOM FOREST FEATURE IMPORTANCE ==========")
    print(importances)
    print(f"\nSaved feature importance: {importance_file}")


if __name__ == "__main__":
    main()
