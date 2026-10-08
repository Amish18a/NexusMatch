# NexusMatch Phase 2 Event + Matchmaking Server

The Phase 2 server connects behavioural telemetry to the existing C++ matchmaking data structures and automatically starts matchmaking when enough compatible players are waiting.

## End-to-end flow

```text
Independent player containers
        ↓
TCP event server
        ↓
PlayerBehaviourTracker
        ↓
14 behavioural features
        ↓
Python Trust ML model
        ↓
Trust Score in C++ Player
        ↓
Queue
        ↓
Hash Table
        ↓
AVL Tree skill search
        ↓
MatchmakingEngine
        ↓
Trust-aware compatibility
        ↓
Match creation
```

## Commands

```text
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
START_MATCHMAKING
SHOW id
SHOW_QUEUE
SHOW_ALL
QUIT
```

## Build

Run from the Phase2 directory:

```powershell
g++ -std=c++17 -pthread ^
  -I .\cpp ^
  -I ..\Phase1\include ^
  cpp\TrustModelBridge.cpp ^
  cpp\PlayerBehaviourTracker.cpp ^
  cpp\NexusMatchServer.cpp ^
  ..\Phase1\src\Player.cpp ^
  ..\Phase1\src\Queue.cpp ^
  ..\Phase1\src\AVLTree.cpp ^
  ..\Phase1\src\HashTable.cpp ^
  ..\Phase1\src\MatchmakingEngine.cpp ^
  ..\Phase1\src\Match.cpp ^
  -lws2_32 ^
  -o cpp\nexusmatch_server.exe
```

Build the client:

```powershell
g++ -std=c++17 cpp\NexusMatchClientDemo.cpp -lws2_32 -o cpp\nexusmatch_client_demo.exe
```

## Docker

From the repository root:

```powershell
docker compose -f Phase2\docker\docker-compose.yml down
docker compose -f Phase2\docker\docker-compose.yml up --build
```

Run the GUI separately:

```powershell
python GUI\main.py
```

The Docker environment and Trust training data are controlled simulations. They validate software integration and reproducible pipeline behaviour, not real-player predictive performance.
