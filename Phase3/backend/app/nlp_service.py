from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from .config import PHASE3_ROOT

NLP_DATA_DIR = PHASE3_ROOT / "backend" / "data" / "nlp"
CORPUS_PATH = NLP_DATA_DIR / "labeled_demo_corpus.csv"
DEMO_BATCH_PATH = NLP_DATA_DIR / "demo_batch.txt"


def get_demo_batch() -> dict[str, Any]:
    if not DEMO_BATCH_PATH.exists():
        raise FileNotFoundError(f"NLP demo batch is missing: {DEMO_BATCH_PATH}")
    messages = [line.strip() for line in DEMO_BATCH_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "messages": messages,
        "source": "Curated synthetic demonstration messages",
        "training_corpus_rows": _count_corpus_rows(),
        "notice": "The included corpus is synthetic and intended only to demonstrate the batch NLP workflow. It is not a validated real-world toxicity dataset.",
    }


def _count_corpus_rows() -> int:
    with CORPUS_PATH.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in csv.DictReader(handle)))


def _load_training_corpus() -> tuple[list[str], np.ndarray]:
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"NLP labelled training corpus is missing: {CORPUS_PATH}")
    texts: list[str] = []
    labels: list[int] = []
    with CORPUS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"text", "toxic"}.issubset(set(reader.fieldnames)):
            raise ValueError("NLP corpus must contain 'text' and 'toxic' columns.")
        for row in reader:
            text = (row.get("text") or "").strip()
            label_text = (row.get("toxic") or "").strip()
            if not text:
                continue
            if label_text not in {"0", "1"}:
                raise ValueError("Every NLP corpus label must be 0 (non-toxic) or 1 (toxic).")
            texts.append(text)
            labels.append(int(label_text))
    y = np.asarray(labels, dtype=np.int64)
    if len(texts) < 20 or len(set(labels)) != 2:
        raise ValueError("NLP training corpus needs at least 20 rows and both classes.")
    if min(np.bincount(y)) < 5:
        raise ValueError("Each NLP class needs at least five examples for validation.")
    return texts, y


def _build_pipeline() -> tuple[TfidfVectorizer, LogisticRegression]:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=1,
        max_features=8000,
        sublinear_tf=True,
    )
    classifier = LogisticRegression(
        max_iter=1200,
        class_weight="balanced",
        random_state=42,
    )
    return vectorizer, classifier


def analyze_batch(messages: list[str], threshold: float = 0.5) -> dict[str, Any]:
    cleaned = [str(message).strip() for message in messages if str(message).strip()]
    if not cleaned:
        raise ValueError("Enter at least one non-empty message to analyse.")
    if len(cleaned) > 500:
        raise ValueError("A single batch can contain at most 500 messages.")
    if not 0.1 <= float(threshold) <= 0.9:
        raise ValueError("Threshold must be between 0.10 and 0.90.")

    corpus_texts, labels = _load_training_corpus()
    x_train, x_test, y_train, y_test = train_test_split(
        corpus_texts,
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels,
    )

    validation_vectorizer, validation_model = _build_pipeline()
    train_matrix = validation_vectorizer.fit_transform(x_train)
    test_matrix = validation_vectorizer.transform(x_test)
    validation_model.fit(train_matrix, y_train)
    test_probability = validation_model.predict_proba(test_matrix)[:, 1]
    test_prediction = (test_probability >= threshold).astype(np.int64)
    matrix = confusion_matrix(y_test, test_prediction, labels=[0, 1])
    validation = {
        "holdout_rows": int(len(y_test)),
        "accuracy": round(float(accuracy_score(y_test, test_prediction)), 4),
        "precision_toxic": round(float(precision_score(y_test, test_prediction, zero_division=0)), 4),
        "recall_toxic": round(float(recall_score(y_test, test_prediction, zero_division=0)), 4),
        "f1_toxic": round(float(f1_score(y_test, test_prediction, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, test_probability)), 4),
        "confusion_matrix": {
            "true_non_toxic_pred_non_toxic": int(matrix[0, 0]),
            "true_non_toxic_pred_toxic": int(matrix[0, 1]),
            "true_toxic_pred_non_toxic": int(matrix[1, 0]),
            "true_toxic_pred_toxic": int(matrix[1, 1]),
        },
    }

    # Refit the demonstration classifier on all available labelled corpus rows
    # before scoring the separate operator-supplied batch.
    vectorizer, model = _build_pipeline()
    full_matrix = vectorizer.fit_transform(corpus_texts)
    model.fit(full_matrix, labels)
    batch_matrix = vectorizer.transform(cleaned)
    probabilities = model.predict_proba(batch_matrix)[:, 1]

    predictions = []
    for index, (text, probability) in enumerate(zip(cleaned, probabilities), start=1):
        score = float(np.clip(probability, 0.0, 1.0))
        flagged = score >= threshold
        predictions.append({
            "row": index,
            "text": text,
            "toxicity_risk": round(score, 4),
            "toxicity_percent": round(score * 100.0, 1),
            "label": "flagged_for_review" if flagged else "not_flagged",
        })

    flagged_rows = [item for item in predictions if item["label"] == "flagged_for_review"]
    flagged_rows.sort(key=lambda item: item["toxicity_risk"], reverse=True)
    risk_bands = {
        "low_below_35_percent": sum(1 for item in predictions if item["toxicity_risk"] < 0.35),
        "review_35_to_65_percent": sum(1 for item in predictions if 0.35 <= item["toxicity_risk"] < 0.65),
        "high_65_percent_or_more": sum(1 for item in predictions if item["toxicity_risk"] >= 0.65),
    }
    flagged_count = len(flagged_rows)

    return {
        "total_messages": len(predictions),
        "flagged_messages": flagged_count,
        "toxicity_rate_percent": round(flagged_count / len(predictions) * 100.0, 2),
        "threshold": float(threshold),
        "risk_bands": risk_bands,
        "validation": validation,
        "flagged_examples": flagged_rows[:20],
        "predictions": predictions,
        "method": "TF-IDF word unigrams/bigrams + Logistic Regression; a stratified 75/25 hold-out evaluation is reported separately.",
        "training_corpus": {
            "rows": int(len(corpus_texts)),
            "non_toxic_rows": int((labels == 0).sum()),
            "toxic_rows": int((labels == 1).sum()),
            "source": "Curated synthetic NexusMatch demonstration corpus",
        },
        "limitations": [
            "The included training corpus is synthetic and small; its validation scores are only an implementation check, not evidence of real-world moderation accuracy.",
            "The classifier detects language patterns represented in its training examples and can miss sarcasm, coded abuse, context, and multilingual messages.",
            "A flagged message is a review suggestion, not a definitive finding that a player is toxic.",
            "This offline analysis is separate from the behavioural Trust model and does not change matchmaking scores.",
        ],
    }
