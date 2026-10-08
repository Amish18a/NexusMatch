"""
NexusMatch - Temporal NLP experiment.

Goal:
    Test whether adding historical chat information improves prediction of a
    player's next observed leaver event.

For every target match, the text document contains ONLY chat from earlier
matches by that player. The target match's chat is never included.

Three models are compared on the exact same split:
    1. Behaviour-only Logistic Regression
    2. NLP-only Logistic Regression using TF-IDF
    3. Behaviour + NLP Logistic Regression

The split matches the current temporal baseline:
    StratifiedGroupKFold, grouped by account_id.

Important:
This is still a research baseline. The Dota dataset does not provide a direct
NexusMatch trust label, so the target is next-match leaver status.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
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
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parents[2]

TEMPORAL_FILE = BASE_DIR / "data" / "ml" / "temporal_trust_dataset.csv"
PLAYER_FILE = (
    BASE_DIR
    / "data"
    / "dota2_processed"
    / "player_behavior_features.csv"
)
CHAT_FILE = (
    BASE_DIR
    / "data"
    / "dota2_processed"
    / "chat_processed.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "ml" / "nlp_results"

RANDOM_STATE = 42
N_SPLITS = 5

BEHAVIOUR_FEATURES = [
    "history_matches",
    "prior_leaver_rate",
    "prior_avg_kda_ratio",
    "prior_avg_gold_per_min",
    "prior_avg_xp_per_min",
    "prior_avg_chat_message_count",
    "prior_avg_avg_message_length",
]

TARGET = "leaver_next_match"


def load_temporal_with_history_text() -> pd.DataFrame:
    """Build cumulative historical chat text for each temporal target row."""
    if not TEMPORAL_FILE.exists():
        raise FileNotFoundError(f"Missing: {TEMPORAL_FILE}")

    if not PLAYER_FILE.exists():
        raise FileNotFoundError(f"Missing: {PLAYER_FILE}")

    if not CHAT_FILE.exists():
        raise FileNotFoundError(f"Missing: {CHAT_FILE}")

    temporal = pd.read_csv(TEMPORAL_FILE)
    players = pd.read_csv(
        PLAYER_FILE,
        usecols=["account_id", "match_id", "player_slot"],
    )
    chat = pd.read_csv(
        CHAT_FILE,
        usecols=["match_id", "slot", "text"],
    )

    temporal["match_id"] = pd.to_numeric(
        temporal["match_id"], errors="coerce"
    )
    temporal["account_id"] = pd.to_numeric(
        temporal["account_id"], errors="coerce"
    )

    players["match_id"] = pd.to_numeric(
        players["match_id"], errors="coerce"
    )
    players["account_id"] = pd.to_numeric(
        players["account_id"], errors="coerce"
    )
    players["player_slot"] = pd.to_numeric(
        players["player_slot"], errors="coerce"
    )

    chat["match_id"] = pd.to_numeric(
        chat["match_id"], errors="coerce"
    )
    chat["slot"] = pd.to_numeric(chat["slot"], errors="coerce")

    chat["text"] = chat["text"].fillna("").astype(str)

    # Reduce ~1.4M chat messages to one text document per player-match.
    chat_match = (
        chat.groupby(["match_id", "slot"], as_index=False)["text"]
        .agg(" ".join)
        .rename(columns={"slot": "player_slot", "text": "match_chat_text"})
    )

    temporal = temporal.merge(
        players.drop_duplicates(
            subset=["account_id", "match_id"]
        ),
        on=["account_id", "match_id"],
        how="left",
        validate="one_to_one",
    )

    temporal = temporal.merge(
        chat_match,
        on=["match_id", "player_slot"],
        how="left",
    )

    temporal["match_chat_text"] = temporal["match_chat_text"].fillna("")

    temporal["start_datetime"] = pd.to_datetime(
        temporal["start_datetime"],
        errors="coerce",
        utc=True,
    )

    temporal = temporal.sort_values(
        ["account_id", "start_datetime", "match_id"]
    ).reset_index(drop=True)

    # Create previous-match-only text. The current match's chat is excluded.
    prior_text_parts = []

    for _, group in temporal.groupby("account_id", sort=False):
        running = []
        for text in group["match_chat_text"].tolist():
            prior_text_parts.append(" ".join(running))
            if text:
                running.append(text)

    # The loop above follows group iteration order. Reconstruct the exact
    # index mapping to avoid relying on group size or original row positions.
    temporal["_row_order"] = np.arange(len(temporal))
    history_series = pd.Series(index=temporal.index, dtype="object")

    for _, group in temporal.groupby("account_id", sort=False):
        running = []
        for index, text in zip(
            group.index,
            group["match_chat_text"].tolist(),
        ):
            history_series.loc[index] = " ".join(running)
            if text:
                running.append(text)

    temporal["prior_chat_text"] = history_series.fillna("")

    return temporal


def get_split(df: pd.DataFrame):
    """Return one reproducible stratified grouped train/test split."""
    splitter = StratifiedGroupKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    train_idx, test_idx = next(
        splitter.split(
            df[BEHAVIOUR_FEATURES],
            df[TARGET],
            groups=df["account_id"],
        )
    )

    return train_idx, test_idx


def evaluate(
    name: str,
    y_test: pd.Series,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
) -> dict:
    result = {
        "model": name,
        "accuracy": accuracy_score(y_test, y_pred),
        "balanced_accuracy": balanced_accuracy_score(
            y_test, y_pred
        ),
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
        "average_precision": average_precision_score(
            y_test, y_prob
        ),
    }

    print(f"\n========== {name.upper()} ==========")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    return result


def main() -> None:
    print("NexusMatch - Temporal NLP Experiment")
    print("=" * 56)

    df = load_temporal_with_history_text()

    df = df.dropna(
        subset=BEHAVIOUR_FEATURES + [TARGET]
    ).copy()

    train_idx, test_idx = get_split(df)

    train = df.iloc[train_idx].copy()
    test = df.iloc[test_idx].copy()

    X_train_num = train[BEHAVIOUR_FEATURES]
    X_test_num = test[BEHAVIOUR_FEATURES]
    y_train = train[TARGET].astype(int)
    y_test = test[TARGET].astype(int)

    print(f"Training rows: {len(train):,}")
    print(f"Testing rows : {len(test):,}")
    print(f"Train leaver rate: {y_train.mean():.4f}")
    print(f"Test leaver rate : {y_test.mean():.4f}")
    print(
        f"Train historical chat documents with text: "
        f"{train['prior_chat_text'].ne('').sum():,}"
    )
    print(
        f"Test historical chat documents with text: "
        f"{test['prior_chat_text'].ne('').sum():,}"
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_num)
    X_test_scaled = scaler.transform(X_test_num)

    results = []

    # 1. Behaviour-only baseline.
    behaviour_model = LogisticRegression(
        class_weight="balanced",
        max_iter=3000,
        random_state=RANDOM_STATE,
    )
    behaviour_model.fit(X_train_scaled, y_train)

    behaviour_prob = behaviour_model.predict_proba(X_test_scaled)[:, 1]
    behaviour_pred = (behaviour_prob >= 0.5).astype(int)

    results.append(
        evaluate(
            "Behaviour-only",
            y_test,
            behaviour_pred,
            behaviour_prob,
        )
    )

    # Fit TF-IDF ONLY on training history text to avoid vocabulary leakage.
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.95,
        max_features=1000,
        sublinear_tf=True,
    )

    X_train_text = vectorizer.fit_transform(
        train["prior_chat_text"]
    )
    X_test_text = vectorizer.transform(
        test["prior_chat_text"]
    )

    print(
        f"\nTF-IDF vocabulary size: "
        f"{len(vectorizer.vocabulary_):,}"
    )

    # 2. NLP-only model.
    nlp_model = LogisticRegression(
        class_weight="balanced",
        max_iter=3000,
        random_state=RANDOM_STATE,
    )
    nlp_model.fit(X_train_text, y_train)

    nlp_prob = nlp_model.predict_proba(X_test_text)[:, 1]
    nlp_pred = (nlp_prob >= 0.5).astype(int)

    results.append(
        evaluate(
            "NLP-only (TF-IDF)",
            y_test,
            nlp_pred,
            nlp_prob,
        )
    )

    # 3. Behaviour + NLP.
    numeric_sparse_train = csr_matrix(X_train_scaled)
    numeric_sparse_test = csr_matrix(X_test_scaled)

    X_train_combined = hstack(
        [numeric_sparse_train, X_train_text],
        format="csr",
    )
    X_test_combined = hstack(
        [numeric_sparse_test, X_test_text],
        format="csr",
    )

    combined_model = LogisticRegression(
        class_weight="balanced",
        max_iter=3000,
        random_state=RANDOM_STATE,
    )
    combined_model.fit(X_train_combined, y_train)

    combined_prob = combined_model.predict_proba(
        X_test_combined
    )[:, 1]
    combined_pred = (combined_prob >= 0.5).astype(int)

    results.append(
        evaluate(
            "Behaviour + NLP",
            y_test,
            combined_pred,
            combined_prob,
        )
    )

    comparison = (
        pd.DataFrame(results)
        .sort_values("average_precision", ascending=False)
        .reset_index(drop=True)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    comparison_file = OUTPUT_DIR / "temporal_nlp_model_comparison.csv"
    comparison.to_csv(comparison_file, index=False)

    print("\n========== MODEL COMPARISON ==========")
    print(comparison.to_string(index=False))
    print(f"\nSaved comparison: {comparison_file}")

    # Save vocabulary terms most associated with the positive class.
    feature_names = np.array(vectorizer.get_feature_names_out())

    text_coef = nlp_model.coef_[0]
    top_indices = np.argsort(text_coef)[-30:][::-1]

    top_terms = pd.DataFrame(
        {
            "term": feature_names[top_indices],
            "coefficient": text_coef[top_indices],
        }
    )

    top_terms_file = OUTPUT_DIR / "top_positive_nlp_terms.csv"
    top_terms.to_csv(top_terms_file, index=False)

    print("\n========== TOP POSITIVE NLP TERMS ==========")
    print(top_terms.to_string(index=False))
    print(f"\nSaved NLP terms: {top_terms_file}")


if __name__ == "__main__":
    main()
