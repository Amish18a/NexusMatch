# NexusMatch - Temporal NLP Experiment

This experiment tests whether adding historical player chat information improves
prediction of the player's next observed leaver event.

## Comparison

All three models use the same train/test split:

1. Behaviour-only Logistic Regression
2. NLP-only Logistic Regression using TF-IDF
3. Behaviour + NLP Logistic Regression

## Leakage prevention

For a target match, the NLP document contains chat only from matches that occurred
before the target match.

The TF-IDF vocabulary is fitted only on the training split and then applied to
the test split.

The train/test split is grouped by `account_id`, matching the current temporal
baseline experiment.

## Run

From `Phase2/TrustSystem`:

```bash
python ml/train_temporal_nlp.py
```

Outputs:

```text
data/ml/nlp_results/
├── temporal_nlp_model_comparison.csv
└── top_positive_nlp_terms.csv
```

## Research interpretation

The main comparison is Average Precision because the next-match leaver target
is highly imbalanced. Accuracy should not be used as the main success measure.

The purpose is not to assume that NLP improves trust. The experiment tests the
hypothesis and should report the result either way.
