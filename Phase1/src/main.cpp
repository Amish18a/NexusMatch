#include <iostream>
#include <vector>

#include "../include/Player.h"
#include "../include/Queue.h"
#include "../include/PriorityQueue.h"
#include "../include/HashTable.h"
#include "../include/AVLTree.h"
#include "../include/MatchmakingEngine.h"
#include "../include/Match.h"


// ============================================================
// CREATE MATCH
// ============================================================

bool createMatch(
    PlayerQueue& queue,
    PriorityQueue& priorityQueue,
    AVLTree& skillTree,
    HashTable& playerTable,
    MatchmakingEngine& matchmaking,
    int matchSize,
    int matchId
)
{
    if (queue.getSize() < matchSize)
    {
        std::cout
            << "\nNot enough players in queue to create a "
            << matchSize
            << "-player match.\n";

        return false;
    }

    // The normal queue maintains arrival order.
    // The front player becomes the matchmaking anchor.
    Player anchor = queue.getFront();

    std::vector<Player> matchedPlayers;

    bool success =
        matchmaking.findGroupMatch(
            anchor,
            skillTree,
            matchSize,
            matchedPlayers
        );

    if (!success)
    {
        std::cout
            << "\nNo suitable "
            << matchSize
            << "-player match found.\n";

        return false;
    }

    // --------------------------------------------------------
    // Create Match
    // --------------------------------------------------------

    Match match(matchId, matchSize);

    for (const Player& player : matchedPlayers)
    {
        match.addPlayer(player);
    }

    // --------------------------------------------------------
    // Remove matched players from all data structures
    // --------------------------------------------------------

    for (const Player& player : matchedPlayers)
    {
        // Normal Queue
        queue.removePlayer(
            player.getId()
        );

        // Priority Queue
        //
        // Phase 1 priority queue is currently a waiting-priority
        // structure. We don't have player-ID removal implemented
        // in it yet, so its integration is demonstrated separately.
        //
        // Do NOT dequeue here because the highest-priority player
        // is not necessarily the matched player.

        // AVL Tree
        skillTree.remove(player);

        // Hash Table
        playerTable.remove(
            player.getId()
        );
    }

    // --------------------------------------------------------
    // Display Match
    // --------------------------------------------------------

    std::cout
        << "\n\n===== MATCH CREATED =====\n";

    match.display();

    std::cout
        << "=========================\n";

    return true;
}


// ============================================================
// MAIN
// ============================================================

int main()
{
    // ========================================================
    // 1. CREATE PLAYERS
    // ========================================================

    Player amish(
        101,
        "Amish",
        1520,
        "India",
        "Ranked",
        42,
        94
    );

    Player gurveer(
        102,
        "Gurveer",
        1490,
        "India",
        "Ranked",
        38,
        91
    );

    Player riya(
        103,
        "Riya",
        1520,
        "India",
        "Ranked",
        51,
        97
    );

    Player player4(
        104,
        "Player4",
        1515,
        "India",
        "Ranked",
        120,
        88
    );

    Player player5(
        105,
        "Player5",
        1800,
        "India",
        "Ranked",
        45,
        95
    );


    // ========================================================
    // 2. CREATE DATA STRUCTURES
    // ========================================================

    PlayerQueue queue(10);

    PriorityQueue priorityQueue;

    HashTable playerTable(10);

    AVLTree skillTree;

    MatchmakingEngine matchmaking;


    // ========================================================
    // 3. PLAYER REGISTRATION
    // ========================================================

    std::cout
        << "\n\n============================================\n";

    std::cout
        << "        NEXUSMATCH - PLAYER REGISTRATION\n";

    std::cout
        << "============================================\n";


    // --------------------------------------------------------
    // Queue
    // --------------------------------------------------------

    queue.enqueue(amish);
    queue.enqueue(gurveer);
    queue.enqueue(riya);
    queue.enqueue(player4);
    queue.enqueue(player5);


    // --------------------------------------------------------
    // Hash Table
    // --------------------------------------------------------

    playerTable.insert(amish);
    playerTable.insert(gurveer);
    playerTable.insert(riya);
    playerTable.insert(player4);
    playerTable.insert(player5);


    // --------------------------------------------------------
    // AVL Tree
    // --------------------------------------------------------

    skillTree.insert(amish);
    skillTree.insert(gurveer);
    skillTree.insert(riya);
    skillTree.insert(player4);
    skillTree.insert(player5);


    // --------------------------------------------------------
    // Priority Queue
    //
    // Waiting priority is simulated for Phase 1.
    // Larger value = longer waiting time / higher priority.
    // --------------------------------------------------------

    priorityQueue.enqueue(
        amish,
        5
    );

    priorityQueue.enqueue(
        gurveer,
        25
    );

    priorityQueue.enqueue(
        riya,
        8
    );

    priorityQueue.enqueue(
        player4,
        40
    );

    priorityQueue.enqueue(
        player5,
        3
    );


    // ========================================================
    // 4. DISPLAY INITIAL SYSTEM STATE
    // ========================================================

    std::cout
        << "\n\n===== INITIAL SYSTEM STATE =====\n";


    // --------------------------------------------------------
    // Queue
    // --------------------------------------------------------

    queue.display();


    // --------------------------------------------------------
    // Priority Queue
    // --------------------------------------------------------

    priorityQueue.display();


    // --------------------------------------------------------
    // Hash Table
    // --------------------------------------------------------

    std::cout
        << "\n===== HASH TABLE =====\n";

    playerTable.display();


    // --------------------------------------------------------
    // AVL Tree
    // --------------------------------------------------------

    skillTree.displayInorder();


    // ========================================================
    // 5. TEST HASH TABLE SEARCH
    // ========================================================

    std::cout
        << "\n\n===== HASH TABLE SEARCH TEST =====\n";

    Player* foundPlayer =
        playerTable.search(103);

    if (foundPlayer != nullptr)
    {
        std::cout
            << "Player found:\n";

        std::cout
            << "ID: "
            << foundPlayer->getId()
            << "\n";

        std::cout
            << "Name: "
            << foundPlayer->getName()
            << "\n";

        std::cout
            << "Skill: "
            << foundPlayer->getSkill()
            << "\n";
    }
    else
    {
        std::cout
            << "Player not found.\n";
    }


    // ========================================================
    // 6. TEST PRIORITY QUEUE
    // ========================================================

    std::cout
        << "\n\n===== PRIORITY QUEUE TEST =====\n";

    Player highestPriority =
        priorityQueue.getHighestPriority();

    std::cout
        << "Highest waiting priority: "
        << highestPriority.getName()
        << "\n";

    std::cout
        << "Priority: "
        << "40"
        << "\n";


    // ========================================================
    // 7. BASIC MATCHMAKING
    // ========================================================

    std::cout
        << "\n\n============================================\n";

    std::cout
        << "          NEXUSMATCH MATCHMAKING\n";

    std::cout
        << "============================================\n";

    createMatch(
        queue,
        priorityQueue,
        skillTree,
        playerTable,
        matchmaking,
        4,
        1
    );


    // ========================================================
    // 8. DISPLAY FINAL SYSTEM STATE
    // ========================================================

    std::cout
        << "\n\n============================================\n";

    std::cout
        << "        SYSTEM STATE AFTER MATCH\n";

    std::cout
        << "============================================\n";


    // --------------------------------------------------------
    // Queue
    // --------------------------------------------------------

    queue.display();


    // --------------------------------------------------------
    // AVL Tree
    // --------------------------------------------------------

    skillTree.displayInorder();


    // --------------------------------------------------------
    // Hash Table
    // --------------------------------------------------------

    std::cout
        << "\n===== HASH TABLE AFTER MATCH =====\n";

    playerTable.display();


    // --------------------------------------------------------
    // Priority Queue
    // --------------------------------------------------------

    std::cout
        << "\n===== PRIORITY QUEUE =====\n";

    priorityQueue.display();


    // ========================================================
    // 9. FINAL MESSAGE
    // ========================================================

    std::cout
        << "\n\n============================================\n";

    std::cout
        << "       PHASE 1 CORE DEMONSTRATION DONE\n";

    std::cout
        << "============================================\n";


    return 0;
}