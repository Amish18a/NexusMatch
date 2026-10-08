# Behaviour Telemetry → ML Trust → Matchmaking

This integration demo converts session events into the same 14 Trust features used by the frozen NexusMatch model.

```text
session events
    ↓
PlayerBehaviourTracker
    ↓
14 Trust features
    ↓
Python ML inference
    ↓
Trust Score
    ↓
C++ Player
    ↓
AVL + MatchmakingEngine
```

## Build

Run from the Phase2 directory:

```powershell
g++ -std=c++17 -I .\cpp -I ..\Phase1\include ^
  cpp\TrustModelBridge.cpp ^
  cpp\PlayerBehaviourTracker.cpp ^
  cpp\nexusmatch_live_feature_demo.cpp ^
  ..\Phase1\src\Player.cpp ^
  ..\Phase1\src\AVLTree.cpp ^
  ..\Phase1\src\MatchmakingEngine.cpp ^
  -o cpp\nexusmatch_live_feature_demo.exe
```

Run:

```powershell
.\cpp\nexusmatch_live_feature_demo.exe
```

The demo uses simulated session events. The network server later supplies the same telemetry schema through TCP events.
