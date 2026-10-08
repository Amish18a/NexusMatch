# NexusMatch 🎮

### AI-Assisted Trust-Aware Multiplayer Matchmaking System

NexusMatch is a real-time multiplayer matchmaking system designed to create balanced and efficient matches using **Data Structures, Algorithms, AI/ML, and network-based player information**.

The system matches players based on factors such as **skill rating, network latency, waiting time, region, game mode, and behavioural trust**.

The core matchmaking engine is developed in **C++**, with Python used for the **AI/ML layer and GUI**. The system follows a client-server architecture to support real-time player connections. **Docker Compose** is used to run the C++ matchmaking server and multiple isolated player-client containers.

---

## 🚀 Project Objectives

- Develop an efficient multiplayer matchmaking engine using C++.
- Apply Data Structures and Algorithms to a real-world problem.
- Match players based on skill compatibility and network conditions.
- Reduce excessive matchmaking waiting time using dynamic matching criteria.
- Maintain fast player lookup and skill-based candidate searching.
- Introduce a behavioural trust mechanism using AI/ML.
- Build a real-time client-server matchmaking environment.
- Experiment with Docker-based network and client simulation.
- Evaluate matchmaking quality using measurable performance metrics.

---

## 🧩 Core Features

- 🎮 Multiplayer player registration
- 📋 Matchmaking waiting queue
- ⭐ Skill-based player matching
- ⚡ Real-time ping/latency measurement
- ⏱️ Automatic waiting-time calculation
- 🔥 Dynamic matchmaking based on waiting time
- ⚖️ Team balancing
- 🔑 Fast player lookup
- 🌳 AVL-based skill searching
- 🛡️ Behaviour-based trust scoring
- 🤖 AI/ML-based suspicious behaviour analysis
- 📊 Match compatibility scoring
- 🌐 Client-server communication
- 🖥️ Python-based GUI and monitoring
- 🐳 Docker-based multi-client/server simulation

---

## 🏗️ System Architecture

```text
                  INDEPENDENT PLAYER CLIENTS
                               │
                               ▼
                    ┌────────────────────┐
                    │   NEXUSMATCH      │
                    │      SERVER        │
                    └─────────┬──────────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
          Player Data      Network Data    Behaviour Data
             │                │                │
             │                ▼                ▼
             │               Ping          ML Analysis
             │                                   │
             │                                   ▼
             │                             Trust Score
             │                                   │
             └────────────────┬──────────────────┘
                              ▼
                   ┌─────────────────────┐
                   │ MATCHMAKING ENGINE  │
                   │         C           │
                   └──────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
       Queue            Priority Queue        Hash Table
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                         AVL Tree
                              │
                              ▼
                    Candidate Selection
                              │
                              ▼
                       Match Scoring
                              │
                              ▼
                       Team Balancing
                              │
                              ▼
                           MATCH


---

## ▶️ Phase 2 Demo

Phase 2 currently runs as:

```text
4 independent Docker player containers
        ↓
C++ TCP NexusMatch Server
        ↓
Behaviour Telemetry
        ↓
Python Trust ML Model
        ↓
Trust Score
        ↓
Queue + Hash Table + AVL Tree
        ↓
Automatic Trust-aware Matchmaking
        ↓
Original Tkinter Monitoring GUI
```

Start the server and four player containers:

```powershell
cd Phase2\TrustSystem
docker compose -f docker\docker-compose.yml down
docker compose -f docker\docker-compose.yml up --build -d
```

Run the monitoring GUI from another terminal:

```powershell
cd <NexusMatch repository>
python GUI\main.py
```

The Docker simulation uses three reliable player profiles and one intentionally
unreliable profile. The data is a controlled development simulation, not real
player telemetry.
