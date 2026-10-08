# NexusMatch Phase 2 Docker

This setup runs the Phase 2 C++ matchmaking server and four independent player-client containers on one Docker network.

## Run

From the repository root:

~~~powershell
docker compose -f Phase2\docker\docker-compose.yml down
docker compose -f Phase2\docker\docker-compose.yml up --build
~~~

The server is published as localhost:5050.

Run the monitoring GUI from another terminal:

~~~powershell
python GUI\main.py
~~~

## Services

~~~text
nexusmatch-server
player-amish
player-gurveer
player-riya
player-player4
~~~

All player services use the same compiled client image with different environment-based player configuration.

## Runtime flow

~~~text
Player container
      ↓ TCP
C++ server
      ↓
Behaviour telemetry
      ↓
TrustModelBridge
      ↓
Python Trust inference
      ↓
Trust Score
      ↓
Automatic matchmaking
~~~

The Docker environment is a controlled development simulation. It validates reproducible client/server integration and matchmaking behaviour, not real-player telemetry or real-world Trust-model performance.
