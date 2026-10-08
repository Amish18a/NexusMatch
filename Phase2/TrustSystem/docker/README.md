# NexusMatch Docker Prototype

This Docker setup runs the Phase 2 C++ event server and the simulated player
client as separate containers on the same Docker network.

## Run

From `Phase2/TrustSystem`:

    docker compose -f docker/docker-compose.yml up --build

The server listens on container port 5050. The compose file publishes it as
`localhost:5050` on the host.

## Architecture

    nexusmatch-server
       |
       | TCP
       v
    player-simulation

The server performs:

    player events -> behaviour tracker -> 14 features -> ML Trust inference

The client generates reliable and unreliable session behaviour for development
and validation. This is simulation telemetry, not real-player data.

## Stop

    docker compose -f docker/docker-compose.yml down

## Important

The current Trust model is a Phase 2 development model trained on synthetic
NexusMatch data. Docker validates reproducible runtime integration; it does not
establish real-world predictive performance.