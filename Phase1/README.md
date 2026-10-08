# NexusMatch Phase 1

Phase 1 is the C++ Data Structures and Algorithms foundation of NexusMatch.

## Components

- **Player** — player identity, skill, region, mode, ping and Trust state
- **Queue** — normal waiting queue
- **Priority Queue** — waiting-priority management
- **Hash Table** — fast player lookup by ID
- **AVL Tree** — skill-ordered candidate search
- **MatchmakingEngine** — candidate filtering and compatibility scoring
- **Match** — representation of a created group

The files under include/ contain declarations; src/ contains implementations and the Phase 1 demonstration program.

## Build

From the repository root:

~~~powershell
g++ -std=c++17 ^
  Phase1\src\main.cpp ^
  Phase1\src\Player.cpp ^
  Phase1\src\Queue.cpp ^
  Phase1\src\PriorityQueue.cpp ^
  Phase1\src\HashTable.cpp ^
  Phase1\src\AVLTree.cpp ^
  Phase1\src\MatchmakingEngine.cpp ^
  Phase1\src\Match.cpp ^
  -I Phase1\include ^
  -o Phase1\nexusmatch_phase1_demo.exe
~~~

Run:

~~~powershell
Phase1\nexusmatch_phase1_demo.exe
~~~

The executable is ignored by Git.
