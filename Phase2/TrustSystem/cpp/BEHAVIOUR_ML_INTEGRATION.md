# Behaviour Telemetry -> ML Trust -> Matchmaking

This demo removes manually entered ML feature vectors from the integration
path. A `PlayerBehaviourTracker` converts session events into the same 14
features used by the final NexusMatch Trust model.

Flow:

    session events
        -> behaviour history
        -> 14 Trust features
        -> Python ML inference
        -> Trust Score
        -> C++ Player
        -> AVL + MatchmakingEngine

## Build

From `Phase2/TrustSystem`:

    g++ -std=c++17 -I .\\cpp -I ..\\..\\Phase1\\include ^
      cpp\\TrustModelBridge.cpp ^
      cpp\\PlayerBehaviourTracker.cpp ^
      cpp\\nexusmatch_live_feature_demo.cpp ^
      ..\\..\\Phase1\\src\\Player.cpp ^
      ..\\..\\Phase1\\src\\AVLTree.cpp ^
      ..\\..\\Phase1\\src\\MatchmakingEngine.cpp ^
      -o cpp\\nexusmatch_live_feature_demo.exe

## Run

    .\\cpp\\nexusmatch_live_feature_demo.exe

The session events in this demo are simulated. Real server/Docker events will
replace them later without changing the ML inference interface.
