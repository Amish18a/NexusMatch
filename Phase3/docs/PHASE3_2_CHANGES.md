# Phase 3.2 — Queue timing and match lifecycle

## What changed

1. **Lookup snapshot reuse** — the exact Server RTT sample shown after a successful player lookup is cached for five minutes. Clicking Add to Session uses that same snapshot rather than measuring a second, slightly different value.
2. **Ping semantics separated** — Server RTT is the live API-gateway-to-C++-server measurement. The C++ MatchmakingEngine's per-player Ping input is the predefined profile's historical average `avg_ping_ms`, shown as profile ping. A static registry lookup cannot measure a unique live internet ping for each player.
3. **Queue duration** — joining the queue records `queue_entered_at`. The API returns the elapsed queue duration for waiting players.
4. **Match wait report** — match creation snapshots the wait duration for each selected player and calculates the group's average. Match history displays both.
5. **Match lifecycle** — newly created records are `ACTIVE`. Operators can `End match` (`COMPLETED`) or `Cancel` (`CANCELLED`). The match record is retained in history.
6. **No simultaneous active-match reuse** — players belonging to an ACTIVE match cannot rejoin the queue. Ending or cancelling releases them so they can queue again.
7. **SQLite migration** — existing Phase 3 v0.1 databases are upgraded additively; existing match records remain in history. Wait durations for matches created before this update are displayed as not recorded.

## Important boundary

NexusMatch currently demonstrates matchmaking and match-group formation. It does not launch an actual game server process for each match. Therefore, End/Cancel closes the matchmaking record and releases player profiles; it does not stop live gameplay.

## API additions

- `POST /api/matches/{match_id}/end`
- `POST /api/matches/{match_id}/cancel`

The `GET /api/session/players` response now includes `queue_wait_seconds`. The `GET /api/matches` response now includes `status`, `ended_at`, `player_wait_seconds`, and `average_wait_seconds`.
