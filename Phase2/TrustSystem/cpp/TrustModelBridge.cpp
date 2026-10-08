#include "TrustModelBridge.h"

#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>

#ifdef _WIN32
    #define NM_POPEN _popen
    #define NM_PCLOSE _pclose
#else
    #define NM_POPEN popen
    #define NM_PCLOSE pclose
#endif

std::string TrustModelBridge::quoteArgument(const std::string& value)
{
#ifdef _WIN32
    std::string quoted = "\"" + value;
    std::size_t backslashes = 0;

    for (char ch : value)
    {
        if (ch == '\\')
        {
            ++backslashes;
            continue;
        }

        if (ch == '"')
        {
            quoted.append(backslashes * 2 + 1, '\\');
            quoted += '"';
            backslashes = 0;
            continue;
        }

        if (backslashes > 0)
        {
            quoted.append(backslashes, '\\');
            backslashes = 0;
        }

        quoted += ch;
    }

    quoted.append(backslashes * 2, '\\');
    quoted += "\"";
    return quoted;
#else
    std::string quoted = "'";
    for (char ch : value)
    {
        if (ch == '\'')
        {
            quoted += "'\\''";
        }
        else
        {
            quoted += ch;
        }
    }
    quoted += "'";
    return quoted;
#endif
}

bool TrustModelBridge::parseResult(
    const std::string& line,
    TrustResult& result
)
{
    std::stringstream stream(line);
    std::string token;
    bool hasRisk = false;
    bool hasTrust = false;
    bool hasLabel = false;
    bool hasThreshold = false;

    while (stream >> token)
    {
        const std::size_t pos = token.find('=');
        if (pos == std::string::npos)
        {
            continue;
        }

        const std::string key = token.substr(0, pos);
        const std::string value = token.substr(pos + 1);

        try
        {
            if (key == "risk")
            {
                result.unreliableRisk = std::stod(value);
                hasRisk = true;
            }
            else if (key == "trust")
            {
                result.trustScore = std::stod(value);
                hasTrust = true;
            }
            else if (key == "label")
            {
                result.label = value;
                hasLabel = true;
            }
            else if (key == "threshold")
            {
                result.threshold = std::stod(value);
                hasThreshold = true;
            }
        }
        catch (...)
        {
            return false;
        }
    }

    return hasRisk && hasTrust && hasLabel && hasThreshold;
}

TrustModelBridge::TrustModelBridge(
    const std::string& python,
    const std::string& script
)
    : pythonExecutable(python),
      inferenceScript(script)
{
}

bool TrustModelBridge::predict(
    const TrustFeatures& f,
    TrustResult& result,
    std::string& errorMessage
) const
{
    std::ostringstream command;

    command << quoteArgument(pythonExecutable)
            << " "
            << quoteArgument(inferenceScript)
            << " --history_sessions " << f.historySessions
            << " --join_success_rate " << f.joinSuccessRate
            << " --queue_abandon_rate " << f.queueAbandonRate
            << " --completion_rate " << f.completionRate
            << " --disconnect_rate " << f.disconnectRate
            << " --reconnect_success_rate " << f.reconnectSuccessRate
            << " --recent_3_join_success_rate " << f.recent3JoinSuccessRate
            << " --recent_3_queue_abandon_rate " << f.recent3QueueAbandonRate
            << " --recent_3_completion_rate " << f.recent3CompletionRate
            << " --recent_3_disconnect_rate " << f.recent3DisconnectRate
            << " --recent_3_reconnect_success_rate " << f.recent3ReconnectSuccessRate
            << " --avg_wait_time_sec " << f.avgWaitTimeSec
            << " --avg_ping_ms " << f.avgPingMs
            << " --avg_chat_messages " << f.avgChatMessages;

    FILE* pipe = NM_POPEN(command.str().c_str(), "r");
    if (pipe == nullptr)
    {
        errorMessage = "Unable to start Python Trust inference process.";
        return false;
    }

    char buffer[512];
    std::string output;

    while (std::fgets(buffer, sizeof(buffer), pipe) != nullptr)
    {
        output += buffer;
    }

    const int exitCode = NM_PCLOSE(pipe);
    if (exitCode != 0)
    {
        errorMessage = "Python Trust inference exited with code "
            + std::to_string(exitCode) + ". Output: " + output;
        return false;
    }

    std::string line;
    std::stringstream outputStream(output);
    while (std::getline(outputStream, line))
    {
        if (line.find("risk=") != std::string::npos &&
            line.find("trust=") != std::string::npos)
        {
            if (parseResult(line, result))
            {
                return true;
            }
        }
    }

    errorMessage = "Could not parse Trust inference output: " + output;
    return false;
}