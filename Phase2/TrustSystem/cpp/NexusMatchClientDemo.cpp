#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

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
        if (sent <= 0) return false;
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
        if (received <= 0) return false;
        if (ch == '\n') return true;
        if (ch != '\r') line += ch;
    }
}

bool sendCommand(SocketHandle socket, const std::string& command)
{
    if (!sendLine(socket, command)) return false;
    std::string response;
    if (!receiveLine(socket, response)) return false;
    std::cout << command << " -> " << response << "\n";
    return true;
}

void recordReliableSessions(SocketHandle socket, int id, int sessions)
{
    for (int i = 0; i < sessions; ++i)
    {
        sendCommand(socket, "CONNECT " + std::to_string(id) +
            (id == 101 ? " Amish" : id == 102 ? " Gurveer" : " Riya")
            + " 1520 India Ranked " + std::to_string(40 + id % 10));
        sendCommand(socket, "JOIN_SUCCESS " + std::to_string(id));
        sendCommand(socket, "QUEUE " + std::to_string(id));
        sendCommand(socket, "MATCH_START " + std::to_string(id));
        sendCommand(socket, "MATCH_COMPLETE " + std::to_string(id));
        if (i % 2 == 0) sendCommand(socket, "CHAT " + std::to_string(id));
        sendCommand(socket, "END_SESSION " + std::to_string(id));
        sendCommand(socket, "DISCONNECT_PLAYER " + std::to_string(id));
    }
}

void recordUnreliableSessions(SocketHandle socket, int id, int sessions)
{
    for (int i = 0; i < sessions; ++i)
    {
        sendCommand(socket, "CONNECT 104 Player4 1520 India Ranked 55");
        sendCommand(socket, "JOIN_FAIL 104");
        sendCommand(socket, "QUEUE 104");
        sendCommand(socket, "ABANDON 104");
        sendCommand(socket, "MATCH_START 104");
        sendCommand(socket, "DISCONNECT 104");
        sendCommand(socket, "END_SESSION 104");
        sendCommand(socket, "DISCONNECT_PLAYER 104");
    }
}

int main()
{
#ifdef _WIN32
    WSADATA data{};
    if (WSAStartup(MAKEWORD(2, 2), &data) != 0)
    {
        std::cerr << "WSAStartup failed.\n";
        return 1;
    }
#endif

    SocketHandle socketHandle = socket(AF_INET, SOCK_STREAM, 0);
    if (socketHandle == INVALID_SOCKET_HANDLE)
    {
        std::cerr << "Could not create client socket.\n";
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    const char* hostEnvironment = std::getenv("NEXUSMATCH_SERVER_HOST");
    const char* portEnvironment = std::getenv("NEXUSMATCH_SERVER_PORT");

    const char* host =
        hostEnvironment != nullptr
        ? hostEnvironment
        : "127.0.0.1";

    const int port =
        portEnvironment != nullptr
        ? std::atoi(portEnvironment)
        : 5050;

    sockaddr_in serverAddress{};
    serverAddress.sin_family = AF_INET;
    serverAddress.sin_port =
        htons(static_cast<unsigned short>(port));

    // Resolve both IPv4 addresses (127.0.0.1) and Docker DNS names
    // (for example, nexusmatch-server).
    addrinfo hints{};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo* resolved = nullptr;
    const std::string portString = std::to_string(port);
    const int resolveResult =
        getaddrinfo(host, portString.c_str(), &hints, &resolved);

    if (resolveResult != 0 || resolved == nullptr)
    {
        std::cerr << "Could not resolve " << host << ":" << port << ".\n";
        closeSocket(socketHandle);
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    sockaddr_in* resolvedAddress =
        reinterpret_cast<sockaddr_in*>(resolved->ai_addr);
    serverAddress.sin_addr = resolvedAddress->sin_addr;
    freeaddrinfo(resolved);

    if (connect(
            socketHandle,
            reinterpret_cast<sockaddr*>(&serverAddress),
            sizeof(serverAddress)
        ) < 0)
    {
        std::cerr << "Could not connect to " << host << ":" << port << ".\n";
        closeSocket(socketHandle);
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    std::string ready;
    receiveLine(socketHandle, ready);
    std::cout << "Server: " << ready << "\n\n";

    recordReliableSessions(socketHandle, 101, 6);
    recordReliableSessions(socketHandle, 102, 6);
    recordReliableSessions(socketHandle, 103, 6);
    recordUnreliableSessions(socketHandle, 104, 6);

    std::cout << "\n========== TRUST PREDICTIONS ==========" << "\n";
    sendCommand(socketHandle, "TRUST 101");
    sendCommand(socketHandle, "TRUST 102");
    sendCommand(socketHandle, "TRUST 103");
    sendCommand(socketHandle, "TRUST 104");

    std::cout << "\n========== PLAYER STATE ==========" << "\n";
    sendCommand(socketHandle, "SHOW 101");
    sendCommand(socketHandle, "SHOW 102");
    sendCommand(socketHandle, "SHOW 103");
    sendCommand(socketHandle, "SHOW 104");

    sendCommand(socketHandle, "QUIT");

    closeSocket(socketHandle);
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}