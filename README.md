# NexusMatch 🎮

### AI-Assisted Trust-Aware Multiplayer Matchmaking System

NexusMatch is a real-time multiplayer matchmaking prototype that combines **Data Structures and Algorithms, C++, AI/ML, behavioural telemetry, networking, and Docker**.

The system evaluates players using skill, ping, waiting time, region, game mode, and behavioural Trust. Phase 2 connects the Trust model to the C++ matchmaking engine through a TCP server and a multi-client Docker simulation.

> **Current status:** Phase 2 is complete and frozen. Phase 3 is reserved for evaluation, stronger data, team balancing, persistence, and final research/presentation work.

## Repository structure

~~~text
NexusMatch/
├── Phase1/
│   ├── include/             # DSA and matchmaking headers
│   ├── src/                 # Phase 1 implementation and demo
│   └── README.md
│
├── Phase2/
│   ├── cpp/                 # TCP server, telemetry, Trust bridge and demos
│   ├── inference/           # Runtime Trust prediction
│   ├── ml/                  # Final Trust pipeline and research experiments
│   ├── simulation/          # Synthetic NexusMatch telemetry generator
│   ├── research/            # Dota 2 behavioural/NLP research
│   ├── docker/              # Dockerfiles and Compose configuration
│   ├── PHASE2_FINAL.md      # Frozen Phase 2 completion record
│   └── README.md
│
├── GUI/                     # Canonical live Tkinter monitoring dashboard
├── .gitignore
├── .dockerignore
└── README.md
~~~

Generated datasets and experiment outputs are intentionally excluded from Git. The code that creates them remains in the repository.

## System architecture

~~~text
Independent Docker player clients
             │
             ▼
      C++ TCP NexusMatch Server
             │
      ┌──────┼─────────┐
      ▼      ▼         ▼
   Player  Telemetry  Network
    Data     │         │
             ▼         ▼
       Behaviour     Ping
        Tracker
             │
             ▼
      14 Trust features
             │
             ▼
     Python Trust inference
             │
             ▼
         Trust Score
             │
             ▼
 Queue + Hash Table + AVL Tree
             │
             ▼
      MatchmakingEngine
             │
             ▼
        Match creation
             │
             ▼
      Tkinter live monitor
~~~

## Phase 1

Phase 1 establishes the C++ matchmaking foundation using Queue, Priority Queue, Hash Table, AVL Tree, MatchmakingEngine, and Match.

See Phase1/README.md.

## Phase 2

Phase 2 adds behavioural telemetry tracking, a 14-feature Trust representation, calibrated Logistic Regression, the C++ → Python inference bridge, a concurrent TCP server, automatic Trust-aware group matchmaking, Docker Compose simulation, and live GUI integration.

See Phase2/README.md and Phase2/PHASE2_FINAL.md.

## Final Trust model

The deployable Phase 2 model is stored at:

    Phase2/ml/artifacts/final_trust_model.joblib

It is trained on controlled synthetic NexusMatch session data.

Final unseen-test metrics:

| Metric | Result |
|---|---:|
| Accuracy | 0.5837 |
| Balanced Accuracy | 0.6141 |
| Precision (unreliable) | 0.4573 |
| Recall (unreliable) | 0.7277 |
| F1 (unreliable) | 0.5617 |
| ROC-AUC | 0.6918 |
| Average Precision | 0.6098 |
| Brier Score | 0.2023 |

These values validate the current research/development pipeline. They are **not** evidence of real-world predictive performance.

## Run the Phase 2 Docker demo

From the repository root:

~~~powershell
docker compose -f Phase2\docker\docker-compose.yml down
docker compose -f Phase2\docker\docker-compose.yml up --build
~~~

Run the monitoring dashboard in another terminal:

~~~powershell
python GUI\main.py
~~~

The demonstration uses three reliable player configurations and one intentionally unreliable configuration. The automatic matchmaker creates a three-player match from compatible reliable players while the unreliable player remains waiting.

## Trust inference

The Python inference entry point can be run directly from the repository root with the 14 required features:

~~~powershell
python Phase2\inference\trust_inference.py ^
  --history_sessions 20 ^
  --join_success_rate 0.95 ^
  --queue_abandon_rate 0.05 ^
  --completion_rate 0.90 ^
  --disconnect_rate 0.05 ^
  --reconnect_success_rate 0.90 ^
  --recent_3_join_success_rate 1.00 ^
  --recent_3_queue_abandon_rate 0.00 ^
  --recent_3_completion_rate 1.00 ^
  --recent_3_disconnect_rate 0.00 ^
  --recent_3_reconnect_success_rate 1.00 ^
  --avg_wait_time_sec 25 ^
  --avg_ping_ms 45 ^
  --avg_chat_messages 3
~~~

## Research

Dota 2 is retained as supporting behavioural/NLP research only. The final Trust model uses NexusMatch-specific synthetic telemetry.

See Phase2/research/README.md.

## Limitations

Phase 2 is a validated prototype, not a production service. The current Trust data and Docker player behaviour are simulated, the server state is in memory, the GUI is monitoring-only, and real-player generalization has not been established.

## Phase 3 handoff

Build on the frozen Phase 2 baseline with controlled matchmaking benchmarks, stronger and more varied telemetry, team-balancing experiments, richer network simulation, persistence, and final paper/presentation work.
