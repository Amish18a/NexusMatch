# NexusMatch Phase 2 Event + Matchmaking Server

The Phase 2 network prototype now connects the behavioural telemetry pipeline
to the existing C++ matchmaking data structures.

## End-to-end flow

    Docker player simulation
        -> TCP event server
        -> PlayerBehaviourTracker
        -> 14 behavioural features
        -> Python Trust ML model
        -> Trust Score in C++ Player
        -> Queue
        -> Hash Table
        -> AVL Tree skill search
        -> MatchmakingEngine
        -> Trust-aware compatibility score
        -> Match creation

## Matchmaking behaviour

The server accepts historical session events first. After Trust scores are
generated, players reconnect and enter the real matchmaking queue.

The `MATCHMAKE playerId matchSize` command:

1. Uses the Hash Table to locate the waiting player.
2. Uses the AVL Tree to collect skill-compatible candidates.
3. Filters by region and game mode.
4. Scores candidates using skill, ping, Trust, and waiting time.
5. Creates a C++ `Match` object.
6. Removes matched players from the Queue, AVL Tree, and Hash Table.

For the Docker demonstration, four players are queued for a three-player match.
Three reliable players should be selected while the intentionally unreliable
Player4 remains in the queue.

## Commands

    CONNECT id name skill region mode ping
    JOIN_SUCCESS id
    JOIN_FAIL id
    QUEUE id
    ABANDON id
    MATCH_START id
    MATCH_COMPLETE id
    DISCONNECT id
    RECONNECT id
    CHAT id
    END_SESSION id
    DISCONNECT_PLAYER id
    TRUST id
    MATCHMAKE id matchSize
    SHOW id
    SHOW_QUEUE
    QUIT

## Build on Windows/MinGW

From `Phase2/TrustSystem`:

    g++ -std=c++17 -I .\cpp -I ..\..\Phase1\include ^
      cpp\TrustModelBridge.cpp ^
      cpp\PlayerBehaviourTracker.cpp ^
      cpp\NexusMatchServer.cpp ^
      ..\..\Phase1\src\Player.cpp ^
      ..\..\Phase1\src\Queue.cpp ^
      ..\..\Phase1\src\AVLTree.cpp ^
      ..\..\Phase1\src\HashTable.cpp ^
      ..\..\Phase1\src\MatchmakingEngine.cpp ^
      ..\..\Phase1\src\Match.cpp ^
      -lws2_32 ^
      -o cpp\nexusmatch_server.exe

    g++ -std=c++17 cpp\NexusMatchClientDemo.cpp ^
      -lws2_32 ^
      -o cpp\nexusmatch_client_demo.exe

## Docker

From `Phase2/TrustSystem`:

    docker compose -f docker\docker-compose.yml down
    docker compose -f docker\docker-compose.yml up --build

The containers simulate six historical sessions for three reliable players and
one intentionally unreliable player, run the Trust model, reconnect all four
players, and perform a three-player trust-aware matchmaking request.

This remains a controlled development simulation, not real player telemetry.
