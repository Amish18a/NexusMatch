"""
NexusMatch - Train baseline Trust models.

Models:
    1. Logistic Regression
    2. Decision Tree
    3. Random Forest

The experiment uses:
    - stratified train/test split
    - class weights for imbalance
    - accuracy, precision, recall, F1 and ROC-AUC
    - confusion matrices
    - Random Forest feature importance

Important:
This is a retrospective research baseline. Because the current Dota dataset
does not contain a true NexusMatch "next-match trust" label, results should
not be presented as a deployment-ready Trust Score model.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE_DIR / "data" / "ml" / "trust_ml_dataset.csv"
OUTPUT_DIR = BASE_DIR / "data" / "ml" / "results"

FEATURES = [
    "avg_kda",
    "avg_gold_per_min",
    "avg_xp_per_min",
    "avg_chat_messages",
    "avg_chat_length",
]

TARGET = "reliable"
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

    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    else:
        y_prob = None

    result = {
        "model": name,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(
            y_test, y_pred, pos_label=0, zero_division=0
        ),
        "recall": recall_score(
            y_test, y_pred, pos_label=0, zero_division=0
        ),
        "f1": f1_score(
            y_test, y_pred, pos_label=0, zero_division=0
        ),
        "roc_auc": (
            roc_auc_score(y_test, y_prob)
            if y_prob is not None
            else float("nan")
        ),
    }

    print(f"\n========== {name.upper()} ==========")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    return result, model


def main() -> None:
    print("NexusMatch - Baseline Trust Model Training")
    print("=" * 52)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "ML dataset not found. Run prepare_trust_dataset.py first."
        )

    df = pd.read_csv(INPUT_FILE)

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=y,
    )

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

    results = []
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
        .sort_values("f1", ascending=False)
        .reset_index(drop=True)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    comparison_file = OUTPUT_DIR / "model_comparison.csv"
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

    importance_file = OUTPUT_DIR / "random_forest_feature_importance.csv"
    importances.to_csv(importance_file, header=True)

    print("\n========== RANDOM FOREST FEATURE IMPORTANCE ==========")
    print(importances)
    print(f"\nSaved feature importance: {importance_file}")


if __name__ == "__main__":
    main()
