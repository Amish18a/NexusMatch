#include "MatchmakingEngine.h"
#include "Player.h"
#include "PlayerBehaviourTracker.h"
#include "TrustModelBridge.h"
#include "AVLTree.h"

#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

struct SimulatedPlayer
{
    Player player;
    PlayerBehaviourTracker tracker;
};

BehaviourSession reliableSession()
{
    BehaviourSession s;
    s.joinAttempts = 1;
    s.successfulJoins = 1;
    s.queueEntries = 1;
    s.queueAbandons = 0;
    s.matchesStarted = 1;
    s.matchesCompleted = 1;
    s.disconnects = 0;
    s.reconnects = 0;
    s.pingMs = 45;
    s.waitTimeSec = 25;
    s.chatMessages = 3;
    return s;
}

BehaviourSession mixedSession()
{
    BehaviourSession s = reliableSession();
    s.successfulJoins = 0;
    s.queueAbandons = 1;
    s.matchesCompleted = 0;
    s.disconnects = 1;
    s.reconnects = 1;
    s.pingMs = 55;
    s.waitTimeSec = 35;
    return s;
}

BehaviourSession unreliableSession()
{
    BehaviourSession s;
    s.joinAttempts = 1;
    s.successfulJoins = 0;
    s.queueEntries = 1;
    s.queueAbandons = 1;
    s.matchesStarted = 1;
    s.matchesCompleted = 0;
    s.disconnects = 1;
    s.reconnects = 0;
    s.pingMs = 70;
    s.waitTimeSec = 60;
    s.chatMessages = 2;
    return s;
}

int main()
{
    std::cout << "============================================\n";
    std::cout << "   NEXUSMATCH EVENT -> ML -> MATCHMAKING\n";
    std::cout << "============================================\n";

    SimulatedPlayer players[] =
    {
        {
            Player(101, "Amish", 1520, "India", "Ranked", 45, 100),
            PlayerBehaviourTracker()
        },
        {
            Player(102, "Gurveer", 1520, "India", "Ranked", 50, 100),
            PlayerBehaviourTracker()
        },
        {
            Player(103, "Riya", 1520, "India", "Ranked", 48, 100),
            PlayerBehaviourTracker()
        },
        {
            Player(104, "Player4", 1520, "India", "Ranked", 55, 100),
            PlayerBehaviourTracker()
        }
    };

    // Build history from session events instead of manually entering the
    // final Trust features.
    for (int i = 0; i < 10; ++i)
    {
        players[0].tracker.addSession(reliableSession());
        players[1].tracker.addSession(
            i < 8 ? reliableSession() : mixedSession()
        );
        players[2].tracker.addSession(reliableSession());
        players[3].tracker.addSession(unreliableSession());
    }

    TrustModelBridge bridge;
    std::cout << "\n========== TELEMETRY -> TRUST ==========" << "\n";
    std::cout << std::fixed << std::setprecision(2);

    for (auto& entry : players)
    {
        TrustFeatures features =
            entry.tracker.buildTrustFeatures();

        TrustResult result{};
        std::string error;

        if (!bridge.predict(features, result, error))
        {
            std::cerr << "Trust prediction failed for "
                      << entry.player.getName()
                      << ": " << error << "\n";
            return 1;
        }

        entry.player.setTrustScore(
            static_cast<int>(result.trustScore + 0.5)
        );

        std::cout
            << entry.player.getName()
            << " | Sessions: " << entry.tracker.sessionCount()
            << " | Risk: " << result.unreliableRisk
            << " | Trust: " << result.trustScore
            << " | Label: " << result.label
            << "\n";
    }

    AVLTree skillTree;
    for (const auto& entry : players)
    {
        skillTree.insert(entry.player);
    }

    MatchmakingEngine matchmaking;
    std::vector<Player> match;

    if (!matchmaking.findGroupMatch(
            players[0].player,
            skillTree,
            3,
            match
        ))
    {
        std::cerr << "\nNo compatible match found.\n";
        return 1;
    }

    std::cout << "\n========== FINAL MATCH ==========" << "\n";
    for (std::size_t i = 0; i < match.size(); ++i)
    {
        std::cout << i + 1 << ". "
                  << match[i].getName()
                  << " | Trust: "
                  << match[i].getTrustScore()
                  << "\n";
    }

    std::cout << "\nRaw session telemetry is converted into the 14 ML features,\n";
    std::cout << "Trust is predicted, and C++ matchmaking consumes the result.\n";

    return 0;
}