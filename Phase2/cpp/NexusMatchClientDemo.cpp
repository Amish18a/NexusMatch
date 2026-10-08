#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
using SocketHandle = SOCKET;
const SocketHandle INVALID_SOCKET_HANDLE = INVALID_SOCKET;
#else
#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>
#include <unistd.h>
using SocketHandle = int;
const SocketHandle INVALID_SOCKET_HANDLE = -1;
#endif

struct PlayerConfig
{
    int id = 101;
    std::string name = "Amish";
    int skill = 1520;
    std::string region = "India";
    std::string mode = "Ranked";
    int ping = 41;
    bool unreliable = false;
    int startDelaySeconds = 5;
    int queueDelaySeconds = 0;
    int lingerSeconds = 15;
};

void closeSocket(SocketHandle socket)
{
#ifdef _WIN32
    closesocket(socket);
#else
    close(socket);
#endif
}

bool sendLine(
    SocketHandle socket,
    const std::string& line
)
{
    const std::string message = line + "\n";
    const char* data = message.c_str();
    std::size_t remaining = message.size();

    while (remaining > 0)
    {
#ifdef _WIN32
        const int sent =
            send(socket, data, static_cast<int>(remaining), 0);
#else
        const ssize_t sent =
            send(socket, data, remaining, 0);
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

bool receiveLine(
    SocketHandle socket,
    std::string& line
)
{
    line.clear();
    char ch = 0;

    while (true)
    {
#ifdef _WIN32
        const int received =
            recv(socket, &ch, 1, 0);
#else
        const ssize_t received =
            recv(socket, &ch, 1, 0);
#endif

        if (received <= 0)
        {
            return false;
        }

        if (ch == '\n')
        {
            return true;
        }

        if (ch != '\r')
        {
            line += ch;
        }

        if (line.size() > 16384)
        {
            return false;
        }
    }
}

bool sendCommand(
    SocketHandle socket,
    const std::string& command
)
{
    if (!sendLine(socket, command))
    {
        return false;
    }

    std::string response;

    if (!receiveLine(socket, response))
    {
        return false;
    }

    std::cout
        << command
        << " -> "
        << response
        << "\n";

    return true;
}

int envInt(
    const char* name,
    int defaultValue
)
{
    const char* value = std::getenv(name);

    if (value == nullptr)
    {
        return defaultValue;
    }

    return std::atoi(value);
}

std::string envString(
    const char* name,
    const std::string& defaultValue
)
{
    const char* value = std::getenv(name);

    if (value == nullptr)
    {
        return defaultValue;
    }

    return value;
}

PlayerConfig loadConfig()
{
    PlayerConfig config;

    config.id =
        envInt("PLAYER_ID", config.id);

    config.name =
        envString("PLAYER_NAME", config.name);

    config.skill =
        envInt("PLAYER_SKILL", config.skill);

    config.region =
        envString("PLAYER_REGION", config.region);

    config.mode =
        envString("PLAYER_MODE", config.mode);

    config.ping =
        envInt("PLAYER_PING", config.ping);

    config.unreliable =
        envInt("PLAYER_UNRELIABLE", 0) != 0;

    config.startDelaySeconds =
        envInt("PLAYER_START_DELAY", config.startDelaySeconds);

    config.queueDelaySeconds =
        envInt("PLAYER_QUEUE_DELAY", config.queueDelaySeconds);

    config.lingerSeconds =
        envInt("PLAYER_LINGER_SECONDS", config.lingerSeconds);

    return config;
}

bool connectToServer(
    const char* host,
    int port,
    SocketHandle& socketHandle
)
{
    for (int attempt = 1; attempt <= 10; ++attempt)
    {
        socketHandle =
            socket(AF_INET, SOCK_STREAM, 0);

        if (socketHandle == INVALID_SOCKET_HANDLE)
        {
            return false;
        }

        sockaddr_in serverAddress{};
        serverAddress.sin_family = AF_INET;
        serverAddress.sin_port =
            htons(
                static_cast<unsigned short>(port)
            );

        addrinfo hints{};
        hints.ai_family = AF_INET;
        hints.ai_socktype = SOCK_STREAM;

        addrinfo* resolved = nullptr;

        const std::string portString =
            std::to_string(port);

        const int resolveResult =
            getaddrinfo(
                host,
                portString.c_str(),
                &hints,
                &resolved
            );

        if (resolveResult == 0 &&
            resolved != nullptr)
        {
            sockaddr_in* resolvedAddress =
                reinterpret_cast<sockaddr_in*>(
                    resolved->ai_addr
                );

            serverAddress.sin_addr =
                resolvedAddress->sin_addr;

            freeaddrinfo(resolved);

            if (connect(
                    socketHandle,
                    reinterpret_cast<sockaddr*>(
                        &serverAddress
                    ),
                    sizeof(serverAddress)
                ) == 0)
            {
                return true;
            }
        }
        else if (resolved != nullptr)
        {
            freeaddrinfo(resolved);
        }

        closeSocket(socketHandle);

        if (attempt < 10)
        {
            std::this_thread::sleep_for(
                std::chrono::seconds(1)
            );
        }
    }

    return false;
}

bool recordReliableSessions(
    SocketHandle socket,
    const PlayerConfig& config,
    int sessions
)
{
    for (int i = 0; i < sessions; ++i)
    {
        const std::string connectCommand =
            "CONNECT "
            + std::to_string(config.id)
            + " "
            + config.name
            + " "
            + std::to_string(config.skill)
            + " "
            + config.region
            + " "
            + config.mode
            + " "
            + std::to_string(config.ping);

        if (!sendCommand(socket, connectCommand)) return false;
        if (!sendCommand(
                socket,
                "JOIN_SUCCESS " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "QUEUE " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "MATCH_START " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "MATCH_COMPLETE " + std::to_string(config.id)
            )) return false;

        if (i % 2 == 0)
        {
            if (!sendCommand(
                    socket,
                    "CHAT " + std::to_string(config.id)
                )) return false;
        }

        if (!sendCommand(
                socket,
                "END_SESSION " + std::to_string(config.id)
            )) return false;

        if (!sendCommand(
                socket,
                "DISCONNECT_PLAYER " + std::to_string(config.id)
            )) return false;
    }

    return true;
}

bool recordUnreliableSessions(
    SocketHandle socket,
    const PlayerConfig& config,
    int sessions
)
{
    for (int i = 0; i < sessions; ++i)
    {
        const std::string connectCommand =
            "CONNECT "
            + std::to_string(config.id)
            + " "
            + config.name
            + " "
            + std::to_string(config.skill)
            + " "
            + config.region
            + " "
            + config.mode
            + " "
            + std::to_string(config.ping);

        if (!sendCommand(socket, connectCommand)) return false;
        if (!sendCommand(
                socket,
                "JOIN_FAIL " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "QUEUE " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "ABANDON " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "MATCH_START " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "DISCONNECT " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "END_SESSION " + std::to_string(config.id)
            )) return false;
        if (!sendCommand(
                socket,
                "DISCONNECT_PLAYER " + std::to_string(config.id)
            )) return false;
    }

    return true;
}

bool runPlayer(
    SocketHandle socket,
    const PlayerConfig& config
)
{
    std::cout
        << "\n============================================\n"
        << "PLAYER CONTAINER: "
        << config.name
        << " ("
        << config.id
        << ")\n"
        << "============================================\n";

    if (config.unreliable)
    {
        if (!recordUnreliableSessions(socket, config, 6))
        {
            return false;
        }
    }
    else
    {
        if (!recordReliableSessions(socket, config, 6))
        {
            return false;
        }
    }

    std::cout
        << "\n["
        << config.name
        << "] Requesting Trust prediction...\n";

    if (!sendCommand(
            socket,
            "TRUST " + std::to_string(config.id)
        ))
    {
        return false;
    }

    if (config.startDelaySeconds > 0)
    {
        std::cout
            << "["
            << config.name
            << "] Waiting "
            << config.startDelaySeconds
            << "s before live matchmaking.\n";

        std::this_thread::sleep_for(
            std::chrono::seconds(
                config.startDelaySeconds
            )
        );
    }

    if (!sendCommand(
            socket,
            "START_MATCHMAKING"
        ))
    {
        return false;
    }

    if (config.queueDelaySeconds > 0)
    {
        std::this_thread::sleep_for(
            std::chrono::seconds(
                config.queueDelaySeconds
            )
        );
    }

    const std::string liveConnect =
        "CONNECT "
        + std::to_string(config.id)
        + " "
        + config.name
        + " "
        + std::to_string(config.skill)
        + " "
        + config.region
        + " "
        + config.mode
        + " "
        + std::to_string(config.ping);

    if (!sendCommand(socket, liveConnect))
    {
        return false;
    }

    std::cout
        << "["
        << config.name
        << "] Entering LIVE matchmaking queue...\n";

    if (!sendCommand(
            socket,
            "QUEUE " + std::to_string(config.id)
        ))
    {
        return false;
    }

    std::cout
        << "["
        << config.name
        << "] Live matchmaking complete for this client.\n";

    if (config.lingerSeconds > 0)
    {
        std::this_thread::sleep_for(
            std::chrono::seconds(
                config.lingerSeconds
            )
        );
    }

    return true;
}

int main()
{
#ifdef _WIN32
    WSADATA data{};

    if (WSAStartup(
            MAKEWORD(2, 2),
            &data
        ) != 0)
    {
        std::cerr
            << "WSAStartup failed.\n";
        return 1;
    }
#endif

    const PlayerConfig config =
        loadConfig();

    const std::string host =
        envString(
            "NEXUSMATCH_SERVER_HOST",
            "127.0.0.1"
        );

    const int port =
        envInt(
            "NEXUSMATCH_SERVER_PORT",
            5050
        );

    SocketHandle socketHandle =
        INVALID_SOCKET_HANDLE;

    if (!connectToServer(
            host.c_str(),
            port,
            socketHandle
        ))
    {
        std::cerr
            << "Could not connect to "
            << host
            << ":"
            << port
            << ".\n";

#ifdef _WIN32
        WSACleanup();
#endif

        return 1;
    }

    std::string ready;

    if (!receiveLine(
            socketHandle,
            ready
        ))
    {
        std::cerr
            << "Could not receive server handshake.\n";

        closeSocket(socketHandle);

#ifdef _WIN32
        WSACleanup();
#endif

        return 1;
    }

    std::cout
        << "["
        << config.name
        << "] Server: "
        << ready
        << "\n";

    const bool success =
        runPlayer(
            socketHandle,
            config
        );

    closeSocket(socketHandle);

#ifdef _WIN32
    WSACleanup();
#endif

    return success ? 0 : 1;
}
