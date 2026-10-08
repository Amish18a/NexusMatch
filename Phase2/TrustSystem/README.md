# NexusMatch Phase 2 - Trust, Networking and Intelligent Matchmaking

Phase 2 extends the Phase 1 C++ matchmaking engine with a behavioural Trust
system, Python ML inference, TCP networking, Docker-based multi-client
simulation, automatic matchmaking, and live monitoring through the original
Tkinter GUI.

## Final Phase 2 architecture

```text
Independent Docker player containers
            ↓
      C++ TCP Event Server
            ↓
    PlayerBehaviourTracker
            ↓
       14 Trust features
            ↓
     Python ML inference
            ↓
        Trust Score
            ↓
 Queue + Hash Table + AVL Tree
            ↓
       MatchmakingEngine
            ↓
  Skill + Ping + Trust + Waiting
            ↓
      Automatic Match
            ↓
      Original Tkinter GUI
```

## Trust model

The final deployment-time Trust model uses a NexusMatch-specific synthetic
behavioural dataset. It is designed around future reliability rather than
same-session outcome leakage.

Prepared dataset:

- 5,000 simulated players
- 125,454 simulated sessions
- 90,454 supervised examples after history construction
- 33,125 positive examples
- 57,329 negative examples
- 14 behavioural features

The target is a future three-session reliability event: an example is positive
when at least one of the next three sessions is unreliable.

The selected final model is Logistic Regression with chronological
train/validation/test splitting and probability calibration. The model is a
Phase 2 research/development model, not a claim of real-world predictive
performance.

### Final unseen-test results

- Accuracy: 0.5837
- Balanced Accuracy: 0.6141
- Precision for unreliable class: 0.4573
- Recall for unreliable class: 0.7277
- F1 for unreliable class: 0.5617
- ROC-AUC: 0.6918
- Average Precision: 0.6098
- Brier score: 0.2023

The model primarily uses behavioural reliability features such as disconnect
rate, join success, queue abandonment, and reconnect success. Ping and waiting
time remain matchmaking features rather than Trust features.

## Dota 2 research work

The Dota 2 dataset is used as a behavioural/NLP research source and for
feature exploration. It is not the final NexusMatch Trust training source.

The experiments showed that retrospective and temporal Dota-based reliability
prediction was too weak to justify using it as the production-style Trust
model. The Dota pipeline therefore remains a research/preprocessing component,
while the final Phase 2 inference model uses controlled NexusMatch telemetry.

## Networking and Docker

The Phase 2 server is a C++ TCP server on port 5050 and supports multiple
concurrent TCP clients.

Docker Compose launches:

```text
nexusmatch-server
player-amish
player-gurveer
player-riya
player-player4
```

Each player container uses the same client image but receives its own player
configuration through environment variables. Three players use reliable
behaviour and Player4 uses an intentionally unreliable development profile.

This is controlled simulation telemetry, not real player telemetry.

## Automatic matchmaking

After Trust scores are calculated, live matchmaking is enabled. When enough
players are waiting, the server automatically:

1. Selects the first waiting player as the anchor.
2. Retrieves skill-compatible candidates from the AVL tree.
3. Applies region and game-mode filtering.
4. Calculates compatibility using skill, ping, Trust and waiting time.
5. Creates a C++ Match object.
6. Removes matched players from Queue, AVL and Hash Table.

The current Docker demonstration creates a three-player match from the reliable
players while the intentionally unreliable Player4 remains waiting.

## Live GUI

The original project GUI remains the only GUI:

    GUI/main.py

It retains the Phase 1 visual design and now reads live state from the C++ TCP
server through SHOW_ALL.

It displays connected player count, queue size, matches created, player ID,
name, skill, region, mode, ping, Trust Score, live status, and recent server
activity.

## Phase 2 status

| Component | Status |
|---|---|
| Behaviour telemetry | Complete |
| 14-feature Trust pipeline | Complete |
| ML training and inference | Complete |
| C++ ML bridge | Complete |
| TCP event server | Complete |
| Automatic matchmaking | Complete |
| Queue / Hash / AVL integration | Complete |
| Docker multi-client simulation | Complete |
| Original GUI live integration | Complete |
| End-to-end demonstration | Complete |

## Run the complete demo

From Phase2/TrustSystem:

```powershell
docker compose -f docker\docker-compose.yml down
docker compose -f docker\docker-compose.yml up --build
```

From a second terminal at the repository root:

```powershell
python GUI\main.py
```

The Phase 2 implementation is now treated as complete. Further work belongs
to Phase 3: evaluation, stronger experiments, broader real-world data,
improved team balancing, and final presentation/research-paper integration.