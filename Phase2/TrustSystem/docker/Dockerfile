FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

COPY Phase2/TrustSystem/requirements.txt /app/Phase2/TrustSystem/requirements.txt
RUN pip install --no-cache-dir -r /app/Phase2/TrustSystem/requirements.txt

COPY Phase1 /app/Phase1
COPY Phase2/TrustSystem /app/Phase2/TrustSystem

WORKDIR /app/Phase2/TrustSystem

RUN g++ -std=c++17 \
    -I ./cpp \
    -I /app/Phase1/include \
    cpp/TrustModelBridge.cpp \
    cpp/PlayerBehaviourTracker.cpp \
    cpp/NexusMatchServer.cpp \
    /app/Phase1/src/Player.cpp \
    -o /usr/local/bin/nexusmatch_server

EXPOSE 5050

CMD ["nexusmatch_server", "5050"]