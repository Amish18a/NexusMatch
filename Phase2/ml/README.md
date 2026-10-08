# NexusMatch Phase 2 Trust ML

This directory contains the frozen Trust-model training pipeline, the frozen model artifact, and the supporting ML experiments used during Phase 2.

## Final pipeline

```text
simulation/generate_nexusmatch_data.py
            ↓
ml/prepare_nexusmatch_trust_dataset.py
            ↓
ml/train_nexusmatch_trust_models.py
            ↓
ml/artifacts/final_trust_model.joblib
            ↓
inference/trust_inference.py
```

The final model is calibrated Logistic Regression using a chronological train/validation/test design on controlled synthetic NexusMatch telemetry.

## Final metrics

```text
Accuracy                0.5837
Balanced Accuracy       0.6141
Precision (unreliable)  0.4573
Recall (unreliable)     0.7277
F1 (unreliable)         0.5617
ROC-AUC                 0.6918
Average Precision       0.6098
Brier Score             0.2023
```

The final deployable artifact is stored in ml/artifacts/.

## Training

Run from the Phase2 directory:

```powershell
python ml\prepare_nexusmatch_trust_dataset.py
python ml\train_nexusmatch_trust_models.py
```

Generated datasets and prediction CSVs are written under data/ml/ and ignored by Git. Final model and metric artifacts are stored in ml/artifacts/.

## Experiments

The experiments/ directory contains temporal, future-window, NLP, and feature-ablation studies retained for research traceability. They are not part of the frozen runtime path.

## Limitation

Synthetic training data is useful for pipeline validation, but the final model must not be described as a real-player predictive model.
