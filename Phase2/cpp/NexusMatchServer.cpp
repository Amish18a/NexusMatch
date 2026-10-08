#include "PlayerBehaviourTracker.h"
#include "TrustModelBridge.h"
#include "Player.h"
#include "Queue.h"
#include "AVLTree.h"
#include "HashTable.h"
#include "MatchmakingEngine.h"
#include "Match.h"

#include <cstdlib>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <thread>
#include <mutex>
#include <atomic>
#include <functional>
#include <vector>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

#ifdef _WIN32
using SocketHandle = SOCKET;
const SocketHandle INVALID_SOCKET_HANDLE = INVALID_SOCKET;
#else
using SocketHandle = int;
const SocketHandle INVALID_SOCKET_HANDLE = -1;
#endif

struct PlayerState
{
    Player player;
    PlayerBehaviourTracker tracker;
    BehaviourSession activeSession{};
    bool connected = false;
};

struct MatchmakingRuntime
{
    PlayerQueue queue{100};
    HashTable playerTable{101};
    AVLTree skillTree;
    MatchmakingEngine engine;
    int nextMatchId = 1;
    bool automaticMatchmakingEnabled = false;
    int lastMatchId = 0;
    std::vector<int> lastMatchedPlayerIds;
    std::vector<std::string> activityLog;
};

void addActivity(
    MatchmakingRuntime& matchmaking,
    const std::string& activity
)
{
    matchmaking.activityLog.push_back(activity);

    const std::size_t maxEntries = 8;

    if (matchmaking.activityLog.size() > maxEntries)
    {
        matchmaking.activityLog.erase(
            matchmaking.activityLog.begin()
        );
    }
}

bool isMonitoringCommand(const std::string& command)
{
    return command == "SHOW_ALL"
        || command == "SHOW_QUEUE"
        || command == "SHOW"
        || command == "START_MATCHMAKING";
}

void closeSocket(SocketHandle socket)
{
#ifdef _WIN32
    closesocket(socket);
#else
    close(socket);
#endif
}

bool sendLine(SocketHandle socket, const std::string& line)
{
    const std::string message = line + "\n";
    const char* data = message.c_str();
    std::size_t remaining = message.size();

    while (remaining > 0)
    {
#ifdef _WIN32
        const int sent = send(socket, data, static_cast<int>(remaining), 0);
#else
        const ssize_t sent = send(socket, data, remaining, 0);
#endif
        if (sent <= 0)
        {
            return false;
        }

        data += sent;
        remaining -= static_cast<std::size_t>(sent);
    }

    return true;
}

bool receiveLine(SocketHandle socket, std::string& line)
{
    line.clear();
    char ch = 0;

    while (true)
    {
#ifdef _WIN32
        const int received = recv(socket, &ch, 1, 0);
#else
        const ssize_t received = recv(socket, &ch, 1, 0);
#endif

        if (received <= 0)
        {
            return !line.empty();
        }

        if (ch == '\n')
        {
            break;
        }

        if (ch != '\r')
        {
            line += ch;
        }

        if (line.size() > 2048)
        {
            return false;
        }
    }

    return true;
}

bool startSocketLayer()
{
#ifdef _WIN32
    WSADATA data{};
    return WSAStartup(MAKEWORD(2, 2), &data) == 0;
#else
    return true;
#endif
}

void stopSocketLayer()
{
#ifdef _WIN32
    WSACleanup();
#endif
}

bool ensureActive(PlayerState& state, std::string& error)
{
    if (!state.connected)
    {
        error = "Player is not connected";
        return false;
    }

    return true;
}

void removeFromMatchmaking(
    PlayerState& state,
    MatchmakingRuntime& matchmaking
)
{
    if (!state.player.isWaiting())
    {
        return;
    }

    matchmaking.queue.removePlayer(state.player.getId());
    matchmaking.skillTree.remove(state.player);
    matchmaking.playerTable.remove(state.player.getId());

    state.player.setWaiting(false);
}

bool addToMatchmaking(
    PlayerState& state,
    MatchmakingRuntime& matchmaking,
    std::string& error
)
{
    if (state.player.isWaiting())
    {
        error = "Player already in matchmaking queue";
        return false;
    }

    if (matchmaking.queue.isFull())
    {
        error = "Matchmaking queue is full";
        return false;
    }

    matchmaking.queue.enqueue(state.player);
    matchmaking.skillTree.insert(state.player);
    matchmaking.playerTable.insert(state.player);
    state.player.setWaiting(true);

    return true;
}

std::string tryAutomaticMatch(
    std::map<int, PlayerState>& players,
    MatchmakingRuntime& matchmaking,
    int matchSize
)
{
    if (matchmaking.queue.getSize() < matchSize)
    {
        return "";
    }

    const Player anchor = matchmaking.queue.getFront();

    std::vector<Player> matchedPlayers;

    const bool success =
        matchmaking.engine.findGroupMatch(
            anchor,
            matchmaking.skillTree,
            matchSize,
            matchedPlayers
        );

    if (!success)
    {
        return "";
    }

    Match match(
        matchmaking.nextMatchId++,
        matchSize
    );

    for (const Player& matchedPlayer : matchedPlayers)
    {
        match.addPlayer(matchedPlayer);
    }

    std::cout
        << "\n========== AUTOMATIC MATCH CREATED =========="
        << "\n";

    std::cout
        << "Match ID: "
        << match.getMatchId()
        << "\n";

    for (std::size_t i = 0; i < matchedPlayers.size(); ++i)
    {
        std::cout
            << i + 1
            << ". "
            << matchedPlayers[i].getName()
            << " | Skill: "
            << matchedPlayers[i].getSkill()
            << " | Trust: "
            << matchedPlayers[i].getTrustScore()
            << "\n";
    }

    matchmaking.lastMatchId = match.getMatchId();
    matchmaking.lastMatchedPlayerIds.clear();

    for (const Player& matchedPlayer : matchedPlayers)
    {
        matchmaking.lastMatchedPlayerIds.push_back(
            matchedPlayer.getId()
        );

        auto found = players.find(matchedPlayer.getId());

        if (found != players.end())
        {
            removeFromMatchmaking(
                found->second,
                matchmaking
            );
        }
    }

    std::ostringstream response;

    response << "MATCH "
             << match.getMatchId()
             << " AUTO_CREATED players=";

    for (std::size_t i = 0; i < matchedPlayers.size(); ++i)
    {
        if (i > 0)
        {
            response << ",";
        }

        response << matchedPlayers[i].getId();
    }

    return response.str();
}

std::string processCommand(
    std::map<int, PlayerState>& players,
    const std::string& input,
    TrustModelBridge& trustBridge,
    MatchmakingRuntime& matchmaking
)
{
    std::istringstream parser(input);
    std::string command;
    parser >> command;

    if (command == "CONNECT")
    {
        int id = 0;
        std::string name;
        int skill = 0;
        std::string region;
        std::string mode;
        int ping = 0;

        if (!(parser >> id >> name >> skill >> region >> mode >> ping))
        {
            return "ERROR CONNECT id name skill region mode ping";
        }

        auto found = players.find(id);

        if (found == players.end())
        {
            Player player(
                id,
                name,
                skill,
                region,
                mode,
                ping,
                100
            );

            PlayerState state;
            state.player = player;
            state.connected = true;
            players.emplace(id, state);
        }
        else
        {
            if (found->second.connected)
            {
                return "ERROR player already connected";
            }

            found->second.connected = true;
            found->second.activeSession = BehaviourSession{};
            found->second.player.setPing(ping);
        }

        return "OK CONNECTED " + std::to_string(id);
    }

    if (command == "SHOW_QUEUE")
    {
        matchmaking.queue.display();
        matchmaking.skillTree.displayInorder();
        return "OK QUEUE_DISPLAYED";
    }

    if (command == "START_MATCHMAKING")
    {
        matchmaking.automaticMatchmakingEnabled = true;
        return "OK AUTOMATIC_MATCHMAKING_ENABLED";
    }

    if (command == "SHOW_ALL")
    {
        std::ostringstream response;

        response << "STATUS players=" << players.size()
                 << " queue=" << matchmaking.queue.getSize()
                 << " last_match=" << matchmaking.lastMatchId;

        if (!matchmaking.lastMatchedPlayerIds.empty())
        {
            response << " matched=";

            for (std::size_t i = 0;
                 i < matchmaking.lastMatchedPlayerIds.size();
                 ++i)
            {
                if (i > 0)
                {
                    response << ",";
                }

                response
                    << matchmaking.lastMatchedPlayerIds[i];
            }
        }

        for (const auto& entry : players)
        {
            const PlayerState& playerState = entry.second;

            response
                << " | player=" << playerState.player.getId()
                << ",name=" << playerState.player.getName()
                << ",skill=" << playerState.player.getSkill()
                << ",ping=" << playerState.player.getPing()
                << ",trust=" << playerState.player.getTrustScore()
                << ",waiting="
                << (playerState.player.isWaiting() ? "yes" : "no")
                << ",connected="
                << (playerState.connected ? "yes" : "no")
                << ",sessions="
                << playerState.tracker.sessionCount();
        }

        response << " | events=";

        for (std::size_t i = 0;
             i < matchmaking.activityLog.size();
             ++i)
        {
            if (i > 0)
            {
                response << "||";
            }

            response << matchmaking.activityLog[i];
        }

        return response.str();
    }

    int id = 0;
    parser >> id;

    if (id <= 0 || players.find(id) == players.end())
    {
        return "ERROR unknown player";
    }

    PlayerState& state = players[id];
    std::string error;

    if (command == "JOIN_SUCCESS")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.joinAttempts += 1;
        state.activeSession.successfulJoins += 1;
        return "OK JOIN_SUCCESS";
    }

    if (command == "JOIN_FAIL")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.joinAttempts += 1;
        return "OK JOIN_FAIL";
    }

    if (command == "QUEUE")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.queueEntries += 1;

        if (!addToMatchmaking(state, matchmaking, error))
        {
            return "ERROR " + error;
        }

        if (matchmaking.automaticMatchmakingEnabled)
        {
            const std::string matchResult =
                tryAutomaticMatch(
                    players,
                    matchmaking,
                    3
                );

            if (!matchResult.empty())
            {
                return "OK QUEUE -> " + matchResult;
            }
        }

        return "OK QUEUE";
    }

    if (command == "ABANDON")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.queueAbandons += 1;
        removeFromMatchmaking(state, matchmaking);
        return "OK ABANDON";
    }

    if (command == "MATCH_START")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.matchesStarted += 1;
        return "OK MATCH_START";
    }

    if (command == "MATCH_COMPLETE")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.matchesCompleted += 1;
        return "OK MATCH_COMPLETE";
    }

    if (command == "DISCONNECT")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.disconnects += 1;
        return "OK DISCONNECT";
    }

    if (command == "RECONNECT")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.reconnects += 1;
        return "OK RECONNECT";
    }

    if (command == "CHAT")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.activeSession.chatMessages += 1;
        return "OK CHAT";
    }

    if (command == "END_SESSION")
    {
        if (!ensureActive(state, error))
        {
            return "ERROR " + error;
        }

        state.tracker.addSession(state.activeSession);
        state.activeSession = BehaviourSession{};
        return "OK SESSION_RECORDED " +
               std::to_string(state.tracker.sessionCount());
    }

    if (command == "DISCONNECT_PLAYER")
    {
        removeFromMatchmaking(state, matchmaking);
        state.connected = false;
        return "OK PLAYER_DISCONNECTED";
    }

    if (command == "TRUST")
    {
        if (state.tracker.sessionCount() == 0)
        {
            return "ERROR no completed history";
        }

        const bool wasWaiting = state.player.isWaiting();

        if (wasWaiting)
        {
            removeFromMatchmaking(state, matchmaking);
        }

        TrustFeatures features =
            state.tracker.buildTrustFeatures();

        TrustResult result{};

        if (!trustBridge.predict(features, result, error))
        {
            return "ERROR " + error;
        }

        state.player.setTrustScore(
            static_cast<int>(result.trustScore + 0.5)
        );

        if (wasWaiting)
        {
            std::string queueError;
            addToMatchmaking(
                state,
                matchmaking,
                queueError
            );
        }

        std::ostringstream response;

        response << "TRUST " << id
                 << " risk=" << result.unreliableRisk
                 << " trust=" << result.trustScore
                 << " label=" << result.label;

        return response.str();
    }

    if (command == "MATCHMAKE")
    {
        int matchSize = 0;

        if (!(parser >> matchSize))
        {
            return "ERROR MATCHMAKE playerId matchSize";
        }

        if (matchSize < 2)
        {
            return "ERROR matchSize must be at least 2";
        }

        Player* anchor = matchmaking.playerTable.search(id);

        if (anchor == nullptr)
        {
            return "ERROR player is not waiting";
        }

        std::vector<Player> matchedPlayers;

        const bool success =
            matchmaking.engine.findGroupMatch(
                *anchor,
                matchmaking.skillTree,
                matchSize,
                matchedPlayers
            );

        if (!success)
        {
            return "ERROR no suitable match found";
        }

        Match match(
            matchmaking.nextMatchId++,
            matchSize
        );

        for (const Player& matchedPlayer : matchedPlayers)
        {
            match.addPlayer(matchedPlayer);
        }

        std::cout
            << "\n========== TRUST-AWARE MATCH ==========" << "\n";

        std::cout
            << "Match ID: "
            << match.getMatchId()
            << "\n";

        for (std::size_t i = 0; i < matchedPlayers.size(); ++i)
        {
            std::cout
                << i + 1
                << ". "
                << matchedPlayers[i].getName()
                << " | Skill: "
                << matchedPlayers[i].getSkill()
                << " | Trust: "
                << matchedPlayers[i].getTrustScore()
                << "\n";
        }

        match.display();

        std::ostringstream response;

        response << "MATCH "
                  << match.getMatchId()
                  << " CREATED players=";

        for (std::size_t i = 0; i < matchedPlayers.size(); ++i)
        {
            if (i > 0)
            {
                response << ",";
            }

            response << matchedPlayers[i].getId();

            PlayerState& matchedState =
                players[matchedPlayers[i].getId()];

            removeFromMatchmaking(
                matchedState,
                matchmaking
            );
        }

        return response.str();
    }

    if (command == "SHOW")
    {
        std::ostringstream response;

        response << "PLAYER "
                 << state.player.getName()
                 << " trust="
                 << state.player.getTrustScore()
                 << " sessions="
                 << state.tracker.sessionCount()
                 << " waiting="
                 << (state.player.isWaiting() ? "yes" : "no");

        return response.str();
    }

    return "ERROR unknown command";
}

void handleClient(
    SocketHandle client,
    std::map<int, PlayerState>& players,
    TrustModelBridge& trustBridge,
    MatchmakingRuntime& matchmaking,
    std::mutex& stateMutex,
    std::atomic<bool>& serverRunning
)
{
    std::cout << "Client connected.\n";

    sendLine(
        client,
        "NEXUSMATCH_SERVER_READY"
    );

    std::string line;

    while (serverRunning && receiveLine(client, line))
    {
        if (line == "QUIT")
        {
            sendLine(client, "OK CLIENT_DISCONNECTED");
            break;
        }

        std::string response;

        {
            std::lock_guard<std::mutex> lock(stateMutex);

            if (line == "SHUTDOWN")
            {
                response = "OK SERVER_SHUTDOWN";
                serverRunning = false;
            }
            else
            {
                response = processCommand(
                    players,
                    line,
                    trustBridge,
                    matchmaking
                );
            }
        }

        if (!line.empty())
        {
            std::istringstream eventParser(line);
            std::string eventCommand;
            eventParser >> eventCommand;

            if (!isMonitoringCommand(eventCommand))
            {
                std::string activity = "[" + eventCommand + "] " + response;
                addActivity(matchmaking, activity);
            }
        }

        std::cout
            << "[EVENT] "
            << line
            << " -> "
            << response
            << "\n";

        if (!sendLine(client, response))
        {
            break;
        }

        if (!serverRunning)
        {
            break;
        }
    }

    closeSocket(client);
    std::cout << "Client disconnected.\n";
}

int main(int argc, char* argv[])
{
    int port = 5050;

    if (argc > 1)
    {
        port = std::atoi(argv[1]);
    }

    if (!startSocketLayer())
    {
        std::cerr << "Could not initialize socket layer.\n";
        return 1;
    }

    SocketHandle serverSocket =
        socket(AF_INET, SOCK_STREAM, 0);

    if (serverSocket == INVALID_SOCKET_HANDLE)
    {
        std::cerr << "Could not create server socket.\n";
        stopSocketLayer();
        return 1;
    }

    int reuse = 1;

#ifdef _WIN32
    setsockopt(
        serverSocket,
        SOL_SOCKET,
        SO_REUSEADDR,
        reinterpret_cast<const char*>(&reuse),
        sizeof(reuse)
    );
#else
    setsockopt(
        serverSocket,
        SOL_SOCKET,
        SO_REUSEADDR,
        &reuse,
        sizeof(reuse)
    );
#endif

    sockaddr_in address{};

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_ANY);
    address.sin_port =
        htons(static_cast<unsigned short>(port));

    if (bind(
            serverSocket,
            reinterpret_cast<sockaddr*>(&address),
            sizeof(address)
        ) < 0)
    {
        std::cerr
            << "Could not bind port "
            << port
            << ".\n";

        closeSocket(serverSocket);
        stopSocketLayer();
        return 1;
    }

    if (listen(serverSocket, 5) < 0)
    {
        std::cerr
            << "Could not listen on port "
            << port
            << ".\n";

        closeSocket(serverSocket);
        stopSocketLayer();
        return 1;
    }

    std::cout
        << "============================================\n";

    std::cout
        << "         NEXUSMATCH PHASE 2 SERVER\n";

    std::cout
        << "============================================\n";

    std::cout
        << "Listening on 0.0.0.0:"
        << port
        << "\n";

    std::cout
        << "Waiting for player/client events...\n";
    std::cout
        << "Multiple clients and monitoring connections supported.\n";

    std::map<int, PlayerState> players;
    TrustModelBridge trustBridge;
    MatchmakingRuntime matchmaking;

    std::mutex stateMutex;
    std::atomic<bool> serverRunning{true};
    std::vector<std::thread> clientThreads;

    while (serverRunning)
    {
        sockaddr_in clientAddress{};

#ifdef _WIN32
        int clientLength =
            sizeof(clientAddress);
#else
        socklen_t clientLength =
            sizeof(clientAddress);
#endif

        SocketHandle client =
            accept(
                serverSocket,
                reinterpret_cast<sockaddr*>(&clientAddress),
                &clientLength
            );

        if (client == INVALID_SOCKET_HANDLE)
        {
            if (serverRunning)
            {
                std::cerr << "Accept failed.\n";
            }
            continue;
        }

        clientThreads.emplace_back(
            handleClient,
            client,
            std::ref(players),
            std::ref(trustBridge),
            std::ref(matchmaking),
            std::ref(stateMutex),
            std::ref(serverRunning)
        );
    }

    for (std::thread& clientThread : clientThreads)
    {
        if (clientThread.joinable())
        {
            clientThread.join();
        }
    }

    closeSocket(serverSocket);
    stopSocketLayer();

    return 0;
}
