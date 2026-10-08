#include "PlayerBehaviourTracker.h"

#include <algorithm>

double PlayerBehaviourTracker::safeRate(
    double numerator,
    double denominator
)
{
    if (denominator <= 0.0)
    {
        return 0.0;
    }

    return numerator / denominator;
}

double PlayerBehaviourTracker::completionRate(
    const BehaviourSession& session
)
{
    if (session.matchesStarted <= 0)
    {
        return 1.0;
    }

    return safeRate(
        session.matchesCompleted,
        session.matchesStarted
    );
}

double PlayerBehaviourTracker::disconnectRate(
    const BehaviourSession& session
)
{
    return session.disconnects > 0 ? 1.0 : 0.0;
}

double PlayerBehaviourTracker::reconnectSuccess(
    const BehaviourSession& session
)
{
    if (session.disconnects <= 0)
    {
        return 1.0;
    }

    return session.reconnects > 0 ? 1.0 : 0.0;
}

void PlayerBehaviourTracker::addSession(
    const BehaviourSession& session
)
{
    sessions.push_back(session);
}

std::size_t PlayerBehaviourTracker::sessionCount() const
{
    return sessions.size();
}

TrustFeatures PlayerBehaviourTracker::buildTrustFeatures() const
{
    TrustFeatures features{};

    features.historySessions =
        static_cast<double>(sessions.size());

    if (sessions.empty())
    {
        return features;
    }

    double totalJoinAttempts = 0.0;
    double totalSuccessfulJoins = 0.0;
    double totalQueueEntries = 0.0;
    double totalQueueAbandons = 0.0;
    double totalMatchesStarted = 0.0;
    double totalMatchesCompleted = 0.0;
    double totalDisconnects = 0.0;
    double totalReconnectSuccesses = 0.0;
    double totalWait = 0.0;
    double totalPing = 0.0;
    double totalChat = 0.0;

    for (const BehaviourSession& session : sessions)
    {
        totalJoinAttempts += session.joinAttempts;
        totalSuccessfulJoins += session.successfulJoins;
        totalQueueEntries += session.queueEntries;
        totalQueueAbandons += session.queueAbandons;
        totalMatchesStarted += session.matchesStarted;
        totalMatchesCompleted += session.matchesCompleted;
        totalDisconnects += disconnectRate(session);
        totalReconnectSuccesses += reconnectSuccess(session);
        totalWait += session.waitTimeSec;
        totalPing += session.pingMs;
        totalChat += session.chatMessages;
    }

    features.joinSuccessRate = safeRate(
        totalSuccessfulJoins,
        totalJoinAttempts
    );

    features.queueAbandonRate = safeRate(
        totalQueueAbandons,
        totalQueueEntries
    );

    features.completionRate = safeRate(
        totalMatchesCompleted,
        totalMatchesStarted
    );

    features.disconnectRate = safeRate(
        totalDisconnects,
        static_cast<double>(sessions.size())
    );

    features.reconnectSuccessRate = safeRate(
        totalReconnectSuccesses,
        static_cast<double>(sessions.size())
    );

    features.avgWaitTimeSec =
        totalWait / sessions.size();

    features.avgPingMs =
        totalPing / sessions.size();

    features.avgChatMessages =
        totalChat / sessions.size();

    const std::size_t recentCount =
        std::min<std::size_t>(3, sessions.size());

    double recentJoinAttempts = 0.0;
    double recentSuccessfulJoins = 0.0;
    double recentQueueEntries = 0.0;
    double recentQueueAbandons = 0.0;
    double recentMatchesStarted = 0.0;
    double recentMatchesCompleted = 0.0;
    double recentDisconnects = 0.0;
    double recentReconnectSuccesses = 0.0;

    for (std::size_t offset = 0; offset < recentCount; ++offset)
    {
        const BehaviourSession& session =
            sessions[sessions.size() - 1 - offset];

        recentJoinAttempts += session.joinAttempts;
        recentSuccessfulJoins += session.successfulJoins;
        recentQueueEntries += session.queueEntries;
        recentQueueAbandons += session.queueAbandons;
        recentMatchesStarted += session.matchesStarted;
        recentMatchesCompleted += session.matchesCompleted;
        recentDisconnects += disconnectRate(session);
        recentReconnectSuccesses += reconnectSuccess(session);
    }

    features.recent3JoinSuccessRate = safeRate(
        recentSuccessfulJoins,
        recentJoinAttempts
    );

    features.recent3QueueAbandonRate = safeRate(
        recentQueueAbandons,
        recentQueueEntries
    );

    features.recent3CompletionRate = safeRate(
        recentMatchesCompleted,
        recentMatchesStarted
    );

    features.recent3DisconnectRate = safeRate(
        recentDisconnects,
        static_cast<double>(recentCount)
    );

    features.recent3ReconnectSuccessRate = safeRate(
        recentReconnectSuccesses,
        static_cast<double>(recentCount)
    );

    return features;
}