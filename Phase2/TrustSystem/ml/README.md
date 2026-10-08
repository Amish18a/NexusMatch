# NexusMatch - ML Trust Baseline

This folder contains the first machine-learning baseline for the Dota 2
behaviour data used by NexusMatch.

## Files

- `prepare_trust_dataset.py`
- `train_trust_models.py`

## Baseline methodology

The first experiment keeps players with at least five recorded matches.

The target is:

- `reliable = 1`: no recorded leaver event
- `reliable = 0`: at least one recorded leaver event

The first model uses:

- `avg_kda`
- `avg_gold_per_min`
- `avg_xp_per_min`
- `avg_chat_messages`
- `avg_chat_length`

The following fields are deliberately excluded from the feature matrix:

- `leaver_rate` and `completion_proxy`, because they directly encode the target.
- `matches_played`, because it is part of the denominator used to compute leaver rate.
- `avg_time_samples`, because a player leaving can directly reduce the observed
  time samples, which would make it a strong form of post-outcome leakage.

This is a **retrospective baseline experiment**. It is useful for testing the
feature/model pipeline, but it should not be described as the final
deployment-time NexusMatch Trust model.

## Run

From `Phase2/TrustSystem`:

```bash
python ml/prepare_trust_dataset.py
python ml/train_trust_models.py
```

Results are written to:

```text
data/ml/
├── trust_ml_dataset.csv
└── results/
    ├── model_comparison.csv
    └── random_forest_feature_importance.csv
```

## Next research step

The stronger version of the experiment should use a temporal setup: use
historical behaviour from previous matches to predict whether the player
leaves the next match. That removes same-match label leakage and is closer to
how a real NexusMatch Trust Score would be used before matchmaking.
