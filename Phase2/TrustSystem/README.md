# Phase 2 - Trust Score Foundation

This module is the first step of the Phase 2 AI/ML work in NexusMatch.

## Purpose

In Phase 1, the matchmaking engine used basic compatibility factors such as skill, ping and waiting time. Phase 2 extends this idea by introducing player reliability as another factor.

The first step is to prepare behavioural player data and calculate a baseline Trust Score. This is a rule-based prototype, not the final machine learning model. The baseline gives us a clear starting point for later AI/ML experiments.

## Current Dota 2 Data Work

We are using four relevant files from the Kaggle **Dota 2 Matches** dataset:

- `match.csv` - match-level context such as duration, game mode, outcome and cluster.
- `players.csv` - player-level performance and behavioural fields, including `leaver_status`.
- `player_time.csv` - time-based gold, last-hit and experience information for player slots.
- `chat.csv` - in-game text messages that can support the planned NLP component.

These four files are imported and preprocessed by `dota2_preprocessing.py`. The script downloads the four files individually through `kagglehub` instead of storing the large raw dataset in the GitHub repository.

## Preprocessing Pipeline

The preprocessing script currently performs:

1. Numeric type conversion and duplicate removal.
2. Match timestamp conversion and duration conversion.
3. Player-side and leaver indicators.
4. KDA calculation and missing-value handling for player performance fields.
5. Cleaning and forward-filling of the time-series statistics.
6. Text normalization for chat while keeping the original message content available for NLP.
7. Chat activity features such as message count, average length and active-chat flag.
8. Joining the four sources into a player-match feature table.
9. Creation of a player-level reliability summary for non-anonymous accounts.

Generated outputs are stored locally under `data/dota2_processed/`.

## Important Limitation

The Dota 2 dataset is useful for behavioural modelling, but it does **not** directly contain all of the fields used by the NexusMatch baseline Trust Score, such as matchmaking join attempts or queue abandonment events.

Therefore, the Dota-derived `leaver_rate` and `completion_proxy` are treated as behavioural proxies rather than as direct replacements for the final NexusMatch trust labels. This keeps the research claim aligned with what the source data actually contains.

## Baseline Trust Score

The current NexusMatch prototype combines four reliability components:

- Join reliability: 35%
- Match completion: 30%
- Connection stability: 20%
- Queue reliability: 15%

The final value is scaled to a score from 0 to 100.

The Dota 2 pipeline is a separate data-preparation stage for developing and testing future behavioural/ML features before they are connected to the final trust model.

## Run the Dota 2 Preprocessing

From the `Phase2/TrustSystem` directory:

```bash
pip install -r requirements.txt
python dota2_preprocessing.py
```

Kaggle authentication may be required by `kagglehub`. The script downloads only the four selected files.

## Phase 2 Next Steps

1. Explore the Dota-derived behavioural features.
2. Decide which features can be used as reliable trust predictors.
3. Add a suitable target/label strategy for ML experiments.
4. Explore suitable NLP features from the chat data as suggested by the mentor.
5. Compare ML models for player reliability.
6. Connect the selected Trust Score features with the C++ matchmaking engine.
7. Display trust-related information in the monitoring GUI.

The current code is intentionally kept modular so that the data-preparation stage can be tested independently before integration with the main matchmaking engine.
