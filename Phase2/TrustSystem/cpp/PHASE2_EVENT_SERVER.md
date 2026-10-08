# NexusMatch Phase 2 Event Server

This is the first networked Phase 2 server prototype. A localhost TCP client
sends player/session events to the C++ server. The server converts those events
into behaviour history, invokes the trained Python Trust model, and stores the
result in the C++ Player object.

Flow:

    TCP Client
        -> C++ Event Server
        -> PlayerBehaviourTracker
        -> TrustModelBridge
        -> Python ML model
        -> Trust Score

## Build on Windows/MinGW

From `Phase2/TrustSystem`:

    g++ -std=c++17 -I .\\cpp -I ..\\..\\Phase1\\include ^
      cpp\\TrustModelBridge.cpp ^
      cpp\\PlayerBehaviourTracker.cpp ^
      cpp\\NexusMatchServer.cpp ^
      ..\\..\\Phase1\\src\\Player.cpp ^
      -lws2_32 ^
      -o cpp\\nexusmatch_server.exe

    g++ -std=c++17 cpp\\NexusMatchClientDemo.cpp ^
      -lws2_32 ^
      -o cpp\\nexusmatch_client_demo.exe

## Run

Terminal 1:

    .\\cpp\\nexusmatch_server.exe

Terminal 2:

    .\\cpp\\nexusmatch_client_demo.exe

The client creates six historical sessions for three reliable players and one
unreliable player, then requests Trust predictions from the server.

This is still a local development simulation. Docker will later replace the
single demo client with multiple isolated player containers.