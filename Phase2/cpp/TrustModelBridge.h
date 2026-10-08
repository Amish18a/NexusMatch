#ifndef TRUST_MODEL_BRIDGE_H
#define TRUST_MODEL_BRIDGE_H

#include <string>

struct TrustFeatures
{
    double historySessions;
    double joinSuccessRate;
    double queueAbandonRate;
    double completionRate;
    double disconnectRate;
    double reconnectSuccessRate;
    double recent3JoinSuccessRate;
    double recent3QueueAbandonRate;
    double recent3CompletionRate;
    double recent3DisconnectRate;
    double recent3ReconnectSuccessRate;
    double avgWaitTimeSec;
    double avgPingMs;
    double avgChatMessages;
};

struct TrustResult
{
    double unreliableRisk;
    double trustScore;
    std::string label;
    double threshold;
};

class TrustModelBridge
{
private:
    std::string pythonExecutable;
    std::string inferenceScript;

    static std::string quoteArgument(const std::string& value);
    static bool parseResult(const std::string& line, TrustResult& result);

public:
    TrustModelBridge(
        const std::string& python = "python",
        const std::string& script = "inference/trust_inference.py"
    );

    bool predict(
        const TrustFeatures& features,
        TrustResult& result,
        std::string& errorMessage
    ) const;
};

#endif