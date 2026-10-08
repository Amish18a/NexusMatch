FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

COPY Phase2/requirements-docker.txt /app/Phase2/requirements-docker.txt
RUN pip install --no-cache-dir -r /app/Phase2/requirements-docker.txt

COPY Phase1 /app/Phase1
COPY Phase2/cpp /app/Phase2/cpp
COPY Phase2/inference /app/Phase2/inference
COPY Phase2/ml/artifacts/final_trust_model.joblib /app/Phase2/ml/artifacts/final_trust_model.joblib

WORKDIR /app/Phase2

RUN g++ -std=c++17 -pthread \
    -I ./cpp \
    -I /app/Phase1/include \
    cpp/TrustModelBridge.cpp \
    cpp/PlayerBehaviourTracker.cpp \
    cpp/NexusMatchServer.cpp \
    /app/Phase1/src/Player.cpp \
    /app/Phase1/src/Queue.cpp \
    /app/Phase1/src/AVLTree.cpp \
    /app/Phase1/src/HashTable.cpp \
    /app/Phase1/src/MatchmakingEngine.cpp \
    /app/Phase1/src/Match.cpp \
    -o /usr/local/bin/nexusmatch_server

EXPOSE 5050
CMD ["nexusmatch_server", "5050"]
