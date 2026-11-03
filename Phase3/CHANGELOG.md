# NexusMatch Phase 3 changelog

## 0.6.0 — Match history durability and code verification

- Separate the durable SQLite/API match ID from the C++ server's process-local match ID.
- Stop using `INSERT OR REPLACE` with a C++ match ID, preventing match history from being overwritten when the C++ process restarts its counter at 1.
- Add an additive SQLite migration that records the historical C++ ID for existing match rows.
- Return both `match_id` (durable API/history key) and `cpp_match_id` (C++ runtime ID) from match creation.
- Add regression tests for database migration, match lifecycle, duplicate C++ IDs after simulated restarts, HTTP session/queue/match/history flow, and NLP batch analysis.
- Expand the backend test suite from 8 to 16 tests.

## 0.5.0 — Live waiting-time integration

- Synchronise elapsed queue age from the persisted SQLite queue-entry timestamp into C++ on each status refresh and immediately before matchmaking.
- Update the canonical player state and its Queue, AVL Tree and Hash Table copies; the in-place queue update preserves FIFO position.
- Change the 10% waiting contribution to the average capped wait of anchor and candidate, so a longer-waiting candidate can receive a higher ranking contribution.
- Reset the C++ wait value for new queue entries and after leaving the queue.
- Extend the offline evaluator with a controlled synthetic queue-age scenario and an isolated comparison of Trust-aware selection with and without the waiting factor.
- Add queue-wait synchronisation and waiting-factor evaluation tests.

## 0.4.0 — Controlled matchmaking policy evaluation

- Add a Policy Evaluation page to compare skill-only and Trust-aware candidate selection.
- Replay the same predefined ten-player registry across 3-, 4- and 5-player anchor trials.
- Use the existing Phase 2 saved Trust model to score each profile before the replay.
- Compare group skill spread, anchor and pairwise skill gaps, profile-ping spread, average Trust, low-Trust member rate and selection differences.
- Persist benchmark results in the existing structured System Logs; no SQLite schema migration or volume reset is required.
- Explicitly label the benchmark as an offline deterministic replay, not a live match or sequential queue simulation.
- Document that current C++ Player waitingTime is not populated from Phase 3 queue timestamps, so the nominal 10% waiting factor currently contributes zero in live matching.


## 0.3.0 — Offline NLP analysis and matchmaking evaluation

- Add a batch NLP analysis page; no live chat is required.
- Add TF-IDF word unigram/bigram features with a Logistic Regression text classifier.
- Add a labelled synthetic demonstration corpus and a separate sample batch.
- Report a stratified hold-out sanity check, prediction risk bands and flagged-for-review examples.
- Keep NLP separate from behavioural Trust and from the C++ matchmaking score.
- Add additive match database fields for immutable player snapshots and C++ command round-trip timing.
- Add `/api/analytics/summary` and a Match Analytics page for match-size distribution, lifecycle counts, waiting time, Trust, profile ping, skill spread and command timing.
- Record NLP batch runs in the existing structured System Logs.

## 0.2.1 — Queue/session state reconciliation

- Parse the bare player ID emitted at the start of each C++ `SHOW_ALL` player record.
- Reconcile persistent SQLite session records with the C++ server's in-memory player state before queue operations.
- Restore a player's C++ connection and Trust Score if the C++ server restarted while the API database volume remained intact.
- Make queue join idempotent when the C++ server already considers a player queued.
- Make queue removal idempotent when the C++ server has already cleared/lost the player's queue state.
- Clear stale SQLite queue flags and restart the waiting timer when a player is reinserted after a C++ server restart.
- Make adding an already registered active-session player recover/re-synchronize rather than returning a duplicate-session error.

## 0.2.0 — Queue timing and match lifecycle

- Reuse the exact player-lookup RTT snapshot when the operator connects a player.
- Separate live API-to-C++ Server RTT from per-profile historical average ping used by the C++ compatibility calculation.
- Persist queue entry timestamps and calculate live queue wait durations.
- Store individual player wait durations and group average wait in match history.
- Add match `ACTIVE`, `COMPLETED`, and `CANCELLED` states.
- Add End Match and Cancel Match actions in Match History.
- Prevent players from rejoining a queue while they belong to any active match; release them when all their active match records are closed.
- Add safe SQLite v0.1-to-v0.2 additive migrations.


## v0.5.0 — Live Waiting-Time Integration

- Queue timestamps are synchronised into the live C++ Player objects on every status refresh and immediately before matchmaking.
- C++ updates Queue, AVL Tree and Hash Table copies without changing FIFO position.
- Candidate waiting contribution now uses the average capped wait of the anchor and candidate.
- New queue entries reset the C++ wait value; leaving the queue resets it as well.
- Offline evaluation now includes a clearly labelled controlled synthetic queue-age scenario and a wait-neutral comparison.
