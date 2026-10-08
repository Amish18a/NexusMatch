# NexusMatch - Temporal Trust Experiment

The first retrospective Dota baseline showed weak predictive power. The next
experiment uses a temporal setup that is closer to the actual NexusMatch use
case.

## Research question

Can a player's historical behaviour be used to predict whether that player will
leave their next observed match?

## Leakage prevention

For each target match:

- only previous matches are used as model inputs
- the current match's performance and chat are not used as predictors
- all observations for one account are kept in the same train or test fold

This makes the experiment more realistic than the first retrospective baseline.

## Target

`leaver_next_match = 1` means the player is recorded as a leaver in the target
match.

`leaver_next_match = 0` means the player is not recorded as a leaver.

## Historical features

- `history_matches`
- `prior_leaver_rate`
- `prior_avg_kda_ratio`
- `prior_avg_gold_per_min`
- `prior_avg_xp_per_min`
- `prior_avg_chat_message_count`
- `prior_avg_avg_message_length`

Only examples with at least three previous matches are retained.

## Models

- Majority baseline
- Logistic Regression
- Decision Tree
- Random Forest

Metrics include balanced accuracy, leaver precision/recall/F1, ROC-AUC, and
Average Precision.

## Run

From `Phase2/TrustSystem`:

```bash
python ml/prepare_temporal_dataset.py
python ml/train_temporal_models.py
```

Results:

```text
data/ml/temporal_trust_dataset.csv
data/ml/temporal_results/temporal_model_comparison.csv
data/ml/temporal_results/temporal_random_forest_feature_importance.csv
```

The temporal experiment should be treated as the stronger research baseline
for the planned NexusMatch Trust component.
