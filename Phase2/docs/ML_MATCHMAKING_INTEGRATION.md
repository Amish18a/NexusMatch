# ML Trust + C++ Matchmaking Integration

This demo connects the Phase 2 ML Trust inference layer to the existing Phase 1 C++ matchmaking engine.

## Build

Run from the Phase2 directory:

```powershell
g++ -std=c++17 -I .\cpp -I ..\Phase1\include ^
  cpp\TrustModelBridge.cpp ^
  cpp\nexusmatch_trust_matchmaking_demo.cpp ^
  ..\Phase1\src\Player.cpp ^
  ..\Phase1\src\AVLTree.cpp ^
  ..\Phase1\src\MatchmakingEngine.cpp ^
  -o cpp\nexusmatch_trust_matchmaking_demo.exe
```

## Run

```powershell
.\cpp\nexusmatch_trust_matchmaking_demo.exe
```

The demo sends behavioural features to the Python Trust model, stores the resulting Trust Score in C++ Player objects, inserts them into the AVL skill index, and runs the Trust-aware group matchmaking engine.

The model uses synthetic NexusMatch telemetry and is intended for Phase 2 development and pipeline validation.
