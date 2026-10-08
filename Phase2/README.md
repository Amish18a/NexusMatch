# NexusMatch Phase 2

## Status: Complete and frozen

Phase 2 integrates the Phase 1 C++ matchmaking foundation with behavioural Trust estimation, a TCP event server, automatic matchmaking, Docker client simulation, and the canonical Tkinter monitoring GUI.

## Directory guide

| Directory | Purpose |
|---|---|
| cpp/ | TCP server, behaviour tracking, TrustModelBridge and C++ demos |
| inference/ | Runtime Python Trust prediction |
| ml/ | Final Trust training pipeline, artifacts and research experiments |
| simulation/ | Synthetic NexusMatch telemetry generator |
| research/ | Dota 2 behavioural/NLP research and alternative experiments |
| docker/ | Dockerfiles and Docker Compose demo |

## Runtime architecture

~~~text
Docker player clients
        ↓
C++ TCP NexusMatch Server
        ↓
PlayerBehaviourTracker
        ↓
14 Trust features
        ↓
Python Trust inference
        ↓
Trust Score in C++ Player
        ↓
Queue + Hash Table + AVL Tree
        ↓
MatchmakingEngine
        ↓
Automatic Trust-aware match
        ↓
Tkinter monitoring GUI
~~~

## Docker demo

From the repository root:

~~~powershell
docker compose -f Phase2\docker\docker-compose.yml down
docker compose -f Phase2\docker\docker-compose.yml up --build
~~~

Run the GUI separately:

~~~powershell
python GUI\main.py
~~~

The demo starts four isolated player containers. Trust is inferred from historical session behaviour before live queueing. Three compatible reliable players form an automatic three-player match; the intentionally unreliable Player4 remains in the queue.

## Final Trust model

The frozen model is:

    ml/artifacts/final_trust_model.joblib

Final unseen-test metrics:

~~~text
Accuracy:             0.5837
Balanced Accuracy:    0.6141
F1 (unreliable):      0.5617
ROC-AUC:              0.6918
Average Precision:    0.6098
Brier Score:          0.2023
~~~

The model is trained on controlled synthetic NexusMatch telemetry. These metrics are for development and research validation only.

## Frozen decisions

- 14 Trust features
- future three-session unreliability target
- calibrated Logistic Regression
- Dota 2 as supporting behavioural/NLP research
- Trust as a matchmaking factor
- synthetic telemetry as the current development source

Feature-set ablation showed only negligible differences, so Phase 2 is frozen instead of pursuing marginal metric gains.

See PHASE2_FINAL.md for the full completion record and Phase 3 handoff.
