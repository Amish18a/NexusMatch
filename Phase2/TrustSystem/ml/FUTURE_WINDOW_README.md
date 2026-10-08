# NexusMatch - Future-Window Trust Experiment

This is the stronger Trust experiment for Phase 2.

## Research question

Can historical player behaviour predict whether the player will show a leaver
event in at least one of the next three matches?

## Why this target

The earlier next-single-match target was extremely sparse. A three-match future
window better represents short-term player reliability.

## Leakage control

For a prediction point before a target match:

- predictors use only previous matches
- the current and future target matches are not used to calculate predictors
- at least three previous matches are required
- a complete three-match future window is required
- train/validation/test are chronological
- training examples cannot have target windows extending past the training cut

## Features

- history_matches
- prior_leaver_rate
- recent_3_leaver_rate
- historical and recent KDA
- historical and recent gold/min
- historical and recent XP/min
- historical and recent chat activity
- historical and recent average message length

The direct target columns are not features.

## Models

- Historical leaver-rate baseline
- Logistic Regression
- Random Forest
- Extra Trees

Class weights are used for the rare positive class.

The classification threshold is selected on validation rather than fixed at 0.50.

## Metrics

Primary:
1. Average Precision (PR-AUC)
2. Leaver F1

Also reported:
- ROC-AUC
- balanced accuracy
- precision
- recall
- accuracy

## Trust score

For the selected model:

Trust Score = 100 x (1 - predicted leaver risk)

This is a model-derived score. It should not be called a calibrated probability
until formal calibration is evaluated.

## Run

From Phase2/TrustSystem:

    python ml/prepare_future_window_dataset.py
    python ml/train_future_window_models.py

Outputs:

    data/ml/future_window_trust_dataset.csv
    data/ml/future_window_results/validation_model_comparison.csv
    data/ml/future_window_results/final_test_metrics.csv
    data/ml/future_window_results/test_trust_predictions.csv
    data/ml/future_window_results/final_trust_model.joblib
