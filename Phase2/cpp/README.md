# NexusMatch Phase 2 C++

This directory contains the C++ portion of Phase 2: the network server, behavioural telemetry tracker, C++/Python Trust bridge, player client simulator, and focused integration demos.

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

For the live telemetry demo, include PlayerBehaviourTracker.cpp and nexusmatch_live_feature_demo.cpp using the same Phase1 source paths.

## Server and Docker

See ../docs/EVENT_SERVER.md for the complete TCP protocol, Windows build and Docker instructions.

The C++ TrustModelBridge intentionally invokes Python inference as a subprocess. A future production design can replace this with a persistent Trust service.
