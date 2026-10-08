#ifndef PLAYER_BEHAVIOUR_TRACKER_H
#define PLAYER_BEHAVIOUR_TRACKER_H

#include "TrustModelBridge.h"

#include <vector>

struct BehaviourSession
{
    int joinAttempts = 0;
    int successfulJoins = 0;
    int queueEntries = 0;
    int queueAbandons = 0;
    int matchesStarted = 0;
    int matchesCompleted = 0;
    int disconnects = 0;
    int reconnects = 0;
    double pingMs = 0.0;
    double waitTimeSec = 0.0;
    double chatMessages = 0.0;
};

class PlayerBehaviourTracker
{
private:
    std::vector<BehaviourSession> sessions;

    static double safeRate(double numerator, double denominator);
    static double completionRate(const BehaviourSession& session);
    static double disconnectRate(const BehaviourSession& session);
    static double reconnectSuccess(const BehaviourSession& session);

public:
    void addSession(const BehaviourSession& session);

    std::size_t sessionCount() const;

    TrustFeatures buildTrustFeatures() const;
};

#endif