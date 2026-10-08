# ML Trust + C++ Matchmaking Integration

This demo connects the Phase 2 ML Trust inference layer to the existing
Phase 1 C++ matchmaking engine.

## Build

Run from `Phase2/TrustSystem`:

    g++ -std=c++17 -I .\\cpp -I ..\\..\\Phase1\\include ^
      cpp\\TrustModelBridge.cpp ^
      cpp\\nexusmatch_trust_matchmaking_demo.cpp ^
      ..\\..\\Phase1\\src\\Player.cpp ^
      ..\\..\\Phase1\\src\\AVLTree.cpp ^
      ..\\..\\Phase1\\src\\MatchmakingEngine.cpp ^
      -o cpp\\nexusmatch_trust_matchmaking_demo.exe

## Run

    .\\cpp\\nexusmatch_trust_matchmaking_demo.exe

The demo:

1. Sends behavioural features to the trained Python Trust model.
2. Receives unreliable risk and Trust Score.
3. Stores the ML Trust Score in each C++ `Player` object.
4. Inserts those players into the AVL skill index.
5. Runs the existing C++ group matchmaking engine.
6. Uses Trust as part of compatibility scoring.

All sample players have the same skill, region, mode and ping, making the
Trust contribution easy to observe.

The current model is based on synthetic NexusMatch telemetry and is intended
for Phase 2 development and pipeline validation.
