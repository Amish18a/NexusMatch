# Phase 3.3 — Offline NLP and Matchmaking Evaluation

## Scope

This increment adds two presentation and evaluation features without changing the Phase 2 C++ matchmaking decisions or the existing player/queue/match lifecycle.

## Offline NLP analysis

- The NLP page accepts a batch of prepared messages, one message per line.
- The included **131-row labelled corpus** is a small, synthetic demonstration dataset stored at `backend/data/nlp/labeled_demo_corpus.csv`.
- The classifier uses word-level TF-IDF unigrams/bigrams followed by Logistic Regression.
- A stratified 75/25 hold-out check is reported separately from predictions on the operator's message batch. On the included fixed corpus split, the current sanity-check values are accuracy 0.9394, precision 1.0000, recall 0.8824, F1 0.9375 and ROC-AUC 0.9853.
- The operator can change the probability threshold. Messages above the selected threshold are marked **flagged for review**.
- The page calculates an indicator rate: flagged messages divided by all messages in the batch.
- NLP output is not sent to the C++ engine and does not modify the behavioural Trust Score.

### Replace the demonstration corpus

A better evaluation should use a suitably licensed, human-labelled multiplayer communication dataset. Replace `labeled_demo_corpus.csv` with UTF-8 CSV data containing exactly these columns:

```csv
text,toxic
"Nice teamwork, let's regroup",0
"You are a terrible teammate",1
```

Use `0` for non-toxic and `1` for toxic. Keep the classes reasonably represented. The service reads the CSV at analysis time, so a backend rebuild is not required when only the mounted source file is changed, although the API container must be able to read the file.

Do not claim that the included synthetic corpus establishes real-world moderation accuracy. Its hold-out results are a pipeline sanity check only; the 131 examples were curated for a controlled demonstration and do not represent natural player communication at scale. A flagged result is a prompt for human review, not a definitive judgement about a player.

## Matchmaking evaluation

The match table now stores additive evaluation fields:

- a snapshot of each selected player's name, skill, profile ping and Trust at match creation;
- that player's queue wait duration;
- the average group queue wait;
- elapsed time for the API-to-C++ `MATCHMAKE` command/response round trip.

The new `GET /api/analytics/summary` endpoint aggregates:

- active, completed and cancelled matches;
- 3-, 4- and 5-player match distribution;
- unique players and player-match assignments;
- average recorded queue wait;
- average API-to-C++ matchmaking command round-trip;
- average Trust and profile ping for matched player snapshots;
- average per-match skill spread.

Old match rows are preserved by additive SQLite migrations. Matches created before this increment do not have the new player snapshots or command timing, so those particular metrics are excluded where appropriate.

## New API routes

- `GET /api/analytics/summary`
- `GET /api/nlp/demo`
- `POST /api/nlp/analyze`

## Validation performed

- Python modules compiled successfully.
- NLP demo route returned the sample batch.
- NLP analysis route returned predictions, risk bands and a hold-out report.
- Analytics route returned the expected aggregate schema.
- A simulated three-player match route persisted selected-player snapshots and C++ command timing.
- React JSX syntax transpilation passed.
- Existing SQLite database was upgraded with additive columns in a test copy.

A fresh npm/Vite production build and live Docker end-to-end run were not completed in the build environment. Those must be checked on the project machine after rebuilding the web/API images.
