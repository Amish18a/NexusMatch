# Phase 3 — Player registry, Trust and ping semantics

## Player lookup

The operator supplies both Player ID and Player Name. The API performs an exact registry lookup. The website has no create-player endpoint; the seeded registry is read-only from the UI. Skill rating, region and game mode are retrieved from the registry rather than typed by the operator.

The initial registry has ten example profiles in `backend/data/player_profiles.json`. These examples can be edited as project data before the SQLite database is first initialized. After the database is created, change the database deliberately or remove the local development database to reseed it; do not add profile creation to the operator UI.

## Trust

Each registry record contains a prepared 14-feature behavioural history vector. On lookup, the API sends that vector to the existing Phase 2 inference function and receives unreliable risk, Trust Score, label and threshold. The profile histories are simulated and must be described as controlled demonstration data, not real player histories.

When the player is connected to the C++ server, the API sends `SET_TRUST <player_id> <integer_score>`. The new C++ command validates the score range (0–100) and updates the existing Player object. No second matchmaking algorithm or duplicate ML model is introduced.

## Ping

The website measures a complete TCP request/response from the FastAPI gateway to the C++ server (`SHOW_ALL`). That live measurement is displayed as **Server RTT**. Since all ten records are looked up through the same operator application, it is not a distinct public internet ping for each human player.

For the current matchmaking calculation, each predefined profile uses its stored historical `avg_ping_ms` feature as a reproducible simulated per-player ping. This gives the C++ Ping factor meaningful player-to-player variation without pretending the operator's local server RTT belongs to each player. For true per-player live ping in a distributed deployment, each player must have an independently connected client/agent measure RTT to the game/matchmaking server and report it with its authenticated player ID. That is a later network-client extension.

## Matchmaking

The operator first connects selected registry profiles, then explicitly places them in the queue. The operator chooses an anchor player and a group size of 3, 4 or 5. The API sends `MATCHMAKE <anchor_id> <size>` to C++. The existing C++ MatchmakingEngine remains the authority for candidate retrieval, compatibility calculation and match creation.

## Logs

The system log is stored in SQLite and also written to a rotating file. It records profile lookup outcomes, measured gateway RTT, model inference outputs, C++ protocol commands/responses, player connections, queue joins/leaves, matchmaking requests/results, and errors. Docker stdout/stderr remains available through `docker compose logs`; the current UI log viewer is the structured application/protocol audit trail, not a raw Docker daemon log viewer.


## Phase 3.2 clarification

The 2–4 ms sample shown as Server RTT is measured between the API gateway and the C++ matchmaking server. It is an infrastructure health measurement and is not unique to a player. For the ten logical players, the compatibility engine uses the profile's stored `avg_ping_ms` value as that player's simulated network latency. The interface displays these as separate values.

Queue entry time is stored when a player joins the C++ queue through the API. When the C++ engine creates a match, the backend snapshots each selected player's queue duration and the group's average.

Match history now tracks `ACTIVE`, `COMPLETED`, and `CANCELLED`. Ending/cancelling a match closes the match record and releases participants from its active-match lock. This is a matchmaking lifecycle control; there is no separate live game process to terminate in the current prototype.
