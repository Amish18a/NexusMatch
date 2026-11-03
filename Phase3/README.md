# NexusMatch — Phase 3 foundation

Phase 3 turns the Phase 2 prototype into a presenter-operated matchmaking platform. The existing C++ server and Phase 2 Trust model remain the decision-making core. The new web application is an operator interface and API gateway, not a replacement matchmaking engine.

## Decisions locked for the first Phase 3 increment

- The web interface does not create player profiles.
- The player registry contains ten predefined profiles (IDs 101–110).
- An operator enters both Player ID and Player Name; both must match the existing registry record.
- Skill rating, region, game mode and historical behavioural features come from the registry.
- The existing Phase 2 ML model predicts Trust from the stored behavioural feature profile.
- The API measures a live round-trip time from the API gateway to the C++ server and displays it as **Server RTT**. It is not a distinct player's public internet ping.
- The C++ matcher's per-player Ping factor uses each predefined profile's historical average ping (`avg_ping_ms`) from its behavioural feature profile. This gives the ten simulated player profiles different, reproducible latency values. True live per-player internet ping requires an independent client/agent connection for each player; that is a later extension.
- Matchmaking is manually triggered by the operator. Supported group sizes are 3, 4 and 5.
- System logs are persisted in SQLite and also written to a rotating log file.
- Queue entry timestamps are persisted. On each status refresh and immediately before matchmaking, the API sends elapsed queue seconds to the C++ server. The C++ server updates the Player copies in Queue, AVL Tree and Hash Table without changing FIFO order. Match history stores each matched player's higher-resolution queue wait and the group's average.
- Match records have an ACTIVE → COMPLETED or CANCELLED lifecycle. Players cannot enter another queue while they belong to an active match; ending/cancelling the match releases them for another queue.
- NLP analysis is a separate offline/batch page; it is not used as a live chat feature or mixed into the Trust model.
- Match history retains immutable player snapshots and matchmaking command timing for evaluation. SQLite assigns a durable API match ID; the C++ process-local match ID is stored separately because it restarts from 1 after a server restart.
- A Policy Evaluation page compares skill-only and Trust-aware selection over the same predefined profiles without creating live matches.

## Architecture

```text
React web UI
  ├── Player registry lookup (ID + name)
  ├── Session roster and queue controls
  ├── Manual 3/4/5-player matchmaking
  ├── Match history and Trust analytics
  └── Full system log viewer
          │ HTTP / WebSocket
          ▼
Python FastAPI gateway
  ├── Read-only predefined SQLite player registry
  ├── Trust inference using Phase 2 model artifact
  ├── Live gateway-to-C++ RTT probe
  ├── Session/match history and central logs
  ├── Offline NLP batch analysis
  ├── Matchmaking evaluation aggregates
  ├── Skill-only vs Trust-aware policy replay
  ├── Trust-aware with/without waiting-factor ablation
  └── TCP command client
          │ TCP :5050
          ▼
Existing C++ NexusMatch server
  ├── Queue / Hash Table / AVL Tree
  ├── MatchmakingEngine / Match
  └── Trust score applied to Player
```

## Phase 3.6 update procedure (Git Bash)

The C++ Phase 3.5 waiting-time changes are tracked on `phase3-foundation`. The Phase 3.6 application package contains the completed backend, tests and documentation. From the NexusMatch repository root:

```bash
git status
git pull origin phase3-foundation
```

Extract the Phase 3.6 package into the repository root and replace the existing `Phase3` folder. Then rebuild without deleting the persistent data volume:

```bash
docker compose -f Phase3/docker-compose.yml down
docker compose -f Phase3/docker-compose.yml up --build -d
```

Do not use `down -v`; it deletes the SQLite volume containing player session records, match history and system logs. To add the Phase 3 source to your GitHub branch after extracting it:

```bash
git add Phase3
git commit -m "Phase 3: complete backend persistence and tests"
git push origin phase3-foundation
```

## Run with Docker Compose

From the repository root:

```bash
docker compose -f Phase3/docker-compose.yml up --build -d
```

Git Bash uses forward slashes in paths. In PowerShell, use `Phase3\docker-compose.yml`.

Open:

- Web UI: http://localhost:5173
- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/api/health

Stop the Phase 3 stack:

```powershell
docker compose -f Phase3\docker-compose.yml down
```

The Phase 3 SQLite database is stored in the `nexusmatch-phase3-data` Docker volume. The ten initial profiles are seeded from `backend/data/player_profiles.json` on first startup. The web API exposes no profile-creation endpoint.

## Local development without Docker

Terminal 1 — run the existing C++ server using the Phase 2 build instructions.

Terminal 2:

```powershell
cd Phase3\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:NEXUSMATCH_SERVER_HOST="127.0.0.1"
$env:NEXUSMATCH_SERVER_PORT="5050"
uvicorn app.main:app --reload --port 8000
```

Terminal 3:

```powershell
cd Phase3\frontend
npm install
npm run dev
```

## Initial workflow

1. Enter a registered Player ID and the exact Player Name.
2. The API retrieves the existing profile and runs Trust inference on its stored simulated behaviour features.
3. The API measures its live TCP round-trip to the C++ server.
4. Add the profile to the active session; the API sends `CONNECT` and `SET_TRUST` to C++.
5. Join selected players to the queue.
6. Select an anchor player and a group size of 3, 4 or 5; click **Find best match**.
7. The API synchronises elapsed queue seconds into the C++ Player, Queue, AVL Tree and Hash Table copies. C++ executes `MATCHMAKE` using Skill 50%, Ping 20%, Trust 20% and pair waiting 10%; the API records higher-resolution queue waits in match history.
8. The operator can end or cancel an ACTIVE match. This closes the matchmaking record and releases its players; it does not stop a separate game process because NexusMatch currently demonstrates group formation rather than live gameplay.
9. Player lookups, Trust predictions, server commands, queue operations, match creation/closure and errors are recorded in System Logs.
10. Open Policy Evaluation and run the skill-only versus Trust-aware replay; the result is also retained in System Logs.

## Backend verification

From Git Bash:

```bash
cd Phase3/backend
PYTHONPATH=. python -m unittest discover -s tests -v
python -m compileall -q app tests
```

The tests cover additive database migrations, persistent match-history IDs across C++ restarts, match lifecycle/HTTP flow, policy replay, offline NLP analysis and live queue-age synchronisation.

## Current limits to keep visible in the demo

- The ten behavioural profiles are controlled synthetic examples, not real player histories.
- Server RTT is measured from the API gateway to the C++ server. The per-player Ping used by matchmaking is a stored historical average from each simulated profile, not a live player internet test.
- The C++ server's current runtime player store and internal match counter are in memory. SQLite persists the web registry, session snapshots, matches and system logs. The API match ID is generated by SQLite and remains distinct from the C++ process-local ID.
- The current NLP classifier is a demonstration baseline trained on the included 131-row synthetic labelled corpus. It is not validated for real-world moderation. Replace it with a suitable human-labelled dataset before making broader claims.
- Match evaluation snapshots and timing are available for matches created in Phase 3.3 onward. Older records remain in history but may not contain these fields.
- The policy benchmark is a deterministic offline replay, not a sequential queue simulation or live C++ server invocation. Its tie-break may differ from AVL traversal when candidate scores are exactly equal. See `docs/PHASE3_4_EVALUATION.md`.
- The live C++ waiting factor is now populated from Phase 3 queue timestamps. Each candidate score uses the average of the anchor and candidate waiting scores, capped at 100 seconds, multiplied by 10%. The offline benchmark uses a separate controlled synthetic queue-age scenario to test the factor; its wait values are not live observations.


## Phase 3.5 — Live waiting-time integration

See `docs/PHASE3_5_WAITING_TIME.md` for live queue-age synchronisation and `docs/PHASE3_6_MATCH_ID_PERSISTENCE.md` for durable match history IDs.
