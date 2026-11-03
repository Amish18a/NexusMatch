# Phase 3.5 — Live Queue Waiting-Time Integration

## Purpose

This increment connects the queue timer already stored by Phase 3 to the actual C++ matchmaking score. Previously, SQLite and the web UI measured elapsed queue time, but the `Player` objects held by the C++ Queue, AVL Tree and Hash Table retained `waitingTime = 0`.

## Live flow

1. When a player newly joins the queue, the API resets the C++ waiting value to zero and records `queue_entered_at` in SQLite.
2. The website refreshes `/api/status` every 2.5 seconds.
3. The API calculates elapsed seconds from the persisted `queue_entered_at` timestamp.
4. The API sends `SET_WAIT <playerId> <seconds>` to the C++ server.
5. C++ updates the canonical Player state and the Player copies held by Queue, AVL Tree and Hash Table.
6. Immediately before `MATCHMAKE`, the API synchronises the queue again so the calculation uses the latest whole-second values.
7. Match history continues to store the higher-resolution wait duration from SQLite for reporting.

The API can also restore queued players to the C++ process after a server restart. It preserves the persisted queue timestamp when it repairs the C++ queue state.

## Updated waiting component

Each player's waiting contribution is capped at 100 seconds:

```text
waiting_score(player) = min(waiting_seconds, 100)
pair_waiting_score = (anchor_waiting_score + candidate_waiting_score) / 2
```

The pair waiting score contributes 10% of candidate compatibility:

```text
final_score = skill_score * 0.50
            + ping_score  * 0.20
            + trust_score * 0.20
            + pair_waiting_score * 0.10
```

This matters because the anchor's wait value alone is constant across its candidate ranking. Including each candidate's own elapsed queue time allows a longer-waiting candidate to receive a higher waiting contribution, while keeping the anchor's age represented in the pair score.

## Data-structure consistency

The live C++ server stores Player values in several places. `SET_WAIT` therefore updates:

- `PlayerState.player` — canonical session state;
- `PlayerQueue` — in-place update that preserves FIFO position;
- `AVLTree` — remove/reinsert the Player copy using the same skill/ID key;
- `HashTable` — update the stored Player value found by ID.

The queue update is in-place and does not move a player to the back of the queue.

## Benchmark interpretation

The offline policy replay now uses a controlled, deterministic queue-age scenario (0–135 seconds in 15-second steps by profile ID). This is synthetic test input used to verify that the waiting component can change candidate selection. It is not a measurement of real queue sessions. Live match records continue to use actual Phase 3 queue-entry timestamps.

## Verification

- Backend tests cover queue-age synchronisation, recovery/idempotency at API boundaries, and evaluation replay behaviour.
- C++ source changes are on the `phase3-foundation` branch and must be pulled before rebuilding Docker.
- Rebuild the C++ image and API image using `docker compose ... up --build -d`.
- Do not delete the persistent Docker volume.
