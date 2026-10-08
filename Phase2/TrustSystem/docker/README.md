# NexusMatch Docker Phase 2

This Docker setup runs the Phase 2 C++ matchmaking server and four independent
player-client containers on the same Docker network.

## Services

```text
nexusmatch-server
player-amish
player-gurveer
player-riya
player-player4
```

All player services use the same compiled client image. Environment variables
define each player's ID, name, skill, ping and reliability profile.

## Runtime flow

```text
Player container
      ↓ TCP
NexusMatch C++ server
      ↓
Behaviour telemetry
      ↓
TrustModelBridge
      ↓
Python ML model
      ↓
Trust Score
      ↓
Automatic matchmaking
```

## Run

From Phase2/TrustSystem:

```powershell
docker compose -f docker\docker-compose.yml down
docker compose -f docker\docker-compose.yml up --build
```

The server is published as localhost:5050.

Run the monitoring GUI from another terminal at the repository root:

```powershell
python GUI\main.py
```

## Demo behaviour

Three player containers use reliable session behaviour. Player4 uses an
intentionally unreliable profile. After historical sessions, the Trust model
classifies the players, then live matchmaking is enabled.

When three compatible reliable players are available, an automatic three-player
match is created. Player4 remains in the waiting queue because of the low Trust
Score.

## Important limitation

This Docker environment is a controlled development simulation. It validates
reproducible client/server integration and matchmaking behaviour; it does not
represent real player telemetry or establish real-world model performance.