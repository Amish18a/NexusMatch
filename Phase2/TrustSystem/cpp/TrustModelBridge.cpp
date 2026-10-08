#include "TrustModelBridge.h"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

std::string TrustModelBridge::quoteArgument(const std::string& value)
{
#ifdef _WIN32
    std::string quoted = "\"";
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
    // Use std::system() with redirected output instead of popen/pclose.
    // This avoids CRT differences between Windows/MinGW toolchains.
    const auto uniqueId = std::chrono::high_resolution_clock::now()
        .time_since_epoch().count();

    const std::filesystem::path outputFile =
        std::filesystem::temp_directory_path()
        / ("nexusmatch_trust_" + std::to_string(uniqueId) + ".txt");

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
            << " --avg_chat_messages " << f.avgChatMessages
            << " > " << quoteArgument(outputFile.string());

    const int exitCode = std::system(command.str().c_str());

    std::ifstream outputStreamFile(outputFile);
    std::string output(
        (std::istreambuf_iterator<char>(outputStreamFile)),
        std::istreambuf_iterator<char>()
    );
    outputStreamFile.close();

    std::error_code removeError;
    std::filesystem::remove(outputFile, removeError);

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
