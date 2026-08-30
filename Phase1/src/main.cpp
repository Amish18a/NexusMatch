// g++ src/main.cpp src/Player.cpp src/Queue.cpp src/AVLTree.cpp src/HashTable.cpp src/MatchmakingEngine.cpp src/Match.cpp src/PriorityQueue.cpp -o nexusmatch


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
    AVLTree& skillTree,
    HashTable& playerTable,
    MatchmakingEngine& matchmaking,
    int matchSize,
    int matchId
)
{
    // --------------------------------------------------------
    // STEP 1:
    // Check whether enough players are waiting.
    // --------------------------------------------------------

    if (queue.getSize() < matchSize)
    {
        std::cout
            << "\nNot enough players to create a "
            << matchSize
            << "-player match.\n";

        return false;
    }


    // --------------------------------------------------------
    // STEP 2:
    // Select the first player in the normal queue
    // as the matchmaking anchor.
    // --------------------------------------------------------

    Player anchor = queue.getFront();

    std::cout
        << "\n===== MATCHMAKING STARTED =====\n";

    std::cout
        << "Anchor Player: "
        << anchor.getName()
        << "\n";

    std::cout
        << "Anchor Skill: "
        << anchor.getSkill()
        << "\n";


    // --------------------------------------------------------
    // STEP 3:
    // Search the AVL Tree for skill-compatible players.
    // --------------------------------------------------------

    std::vector<Player> matchedPlayers;

    bool success =
        matchmaking.findGroupMatch(
            anchor,
            skillTree,
            matchSize,
            matchedPlayers
        );


    // --------------------------------------------------------
    // STEP 4:
    // If no suitable group is found, stop.
    // --------------------------------------------------------

    if (!success)
    {
        std::cout
            << "\nNo suitable match found.\n";

        return false;
    }


    // --------------------------------------------------------
    // STEP 5:
    // Create the Match object.
    // --------------------------------------------------------

    Match match(
        matchId,
        matchSize
    );


    // --------------------------------------------------------
    // STEP 6:
    // Add selected players to the match.
    // --------------------------------------------------------

    for (const Player& player : matchedPlayers)
    {
        match.addPlayer(player);
    }


    // --------------------------------------------------------
    // STEP 7:
    // Remove matched players from the waiting system.
    // --------------------------------------------------------

    for (const Player& player : matchedPlayers)
    {
        // Remove from normal matchmaking queue
        queue.removePlayer(
            player.getId()
        );

        // Remove from AVL Tree
        skillTree.remove(player);

        // Remove from Hash Table
        playerTable.remove(
            player.getId()
        );
    }


    // --------------------------------------------------------
    // STEP 8:
    // Display the final match.
    // --------------------------------------------------------

    match.display();

    return true;
}


// ============================================================
// MAIN
// ============================================================

int main()
{
    // ========================================================
    // STEP 1 — CREATE PLAYERS
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
    // STEP 2 — CREATE DATA STRUCTURES
    // ========================================================

    PlayerQueue queue(10);

    PriorityQueue priorityQueue;

    HashTable playerTable(10);

    AVLTree skillTree;

    MatchmakingEngine matchmaking;


    // ========================================================
    // STEP 3 — PLAYER REGISTRATION
    // ========================================================

    std::cout
        << "\n============================================\n";

    std::cout
        << "        NEXUSMATCH PLAYER REGISTRATION\n";

    std::cout
        << "============================================\n";


    // --------------------------------------------------------
    // NORMAL QUEUE
    // --------------------------------------------------------

    queue.enqueue(amish);
    queue.enqueue(gurveer);
    queue.enqueue(riya);
    queue.enqueue(player4);
    queue.enqueue(player5);


    // --------------------------------------------------------
    // HASH TABLE
    // Used for fast player-ID lookup.
    // --------------------------------------------------------

    playerTable.insert(amish);
    playerTable.insert(gurveer);
    playerTable.insert(riya);
    playerTable.insert(player4);
    playerTable.insert(player5);


    // --------------------------------------------------------
    // AVL TREE
    // Used for skill-based searching.
    // --------------------------------------------------------

    skillTree.insert(amish);
    skillTree.insert(gurveer);
    skillTree.insert(riya);
    skillTree.insert(player4);
    skillTree.insert(player5);


    // ========================================================
    // STEP 4 — PRIORITY QUEUE
    // ========================================================

    /*
        IMPORTANT:

        Priority Queue is NOT another copy of the normal queue.

        Normal Queue:
        -----------------------------
        Maintains arrival order.

        Priority Queue:
        -----------------------------
        Gives priority to players who
        have waited longer.

        For Phase 1, waiting priority
        is simulated using integer values.

        Higher value = higher priority.
    */

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
    // STEP 5 — DISPLAY SYSTEM STATE
    // ========================================================

    std::cout
        << "\n\n============================================\n";

    std::cout
        << "             CURRENT WAITING PLAYERS\n";

    std::cout
        << "============================================\n";


    std::cout
        << "\n--- NORMAL QUEUE ---\n";

    queue.display();


    std::cout
        << "\n--- PRIORITY QUEUE ---\n";

    priorityQueue.display();


    std::cout
        << "\n--- AVL TREE ---\n";

    skillTree.displayInorder();


    // ========================================================
    // STEP 6 — SHOW PRIORITY DECISION
    // ========================================================

    /*
        The Priority Queue tells us which player
        has the highest waiting priority.

        It does NOT directly choose the whole match.

        The AVL Tree is still responsible for
        finding skill-compatible candidates.
    */

    Player highestPriority =
        priorityQueue.getHighestPriority();


    std::cout
        << "\n\n===== MATCHMAKING PRIORITY =====\n";

    std::cout
        << "Player with highest waiting priority: "
        << highestPriority.getName()
        << "\n";


    // ========================================================
    // STEP 7 — BASIC MATCHMAKING
    // ========================================================

    /*
        For the current Phase 1 prototype:

        Queue
          ↓
        Select anchor
          ↓
        AVL Tree
          ↓
        Skill-compatible candidates
          ↓
        Matchmaking Engine
          ↓
        Compatibility score
          ↓
        Match
    */

    createMatch(
        queue,
        skillTree,
        playerTable,
        matchmaking,
        4,
        1
    );


    // ========================================================
    // STEP 8 — DISPLAY REMAINING SYSTEM
    // ========================================================

    std::cout
        << "\n\n============================================\n";

    std::cout
        << "         SYSTEM AFTER MATCH CREATION\n";

    std::cout
        << "============================================\n";


    // --------------------------------------------------------
    // NORMAL QUEUE
    // --------------------------------------------------------

    std::cout
        << "\n--- NORMAL QUEUE ---\n";

    queue.display();


    // --------------------------------------------------------
    // AVL TREE
    // --------------------------------------------------------

    std::cout
        << "\n--- AVL TREE ---\n";

    skillTree.displayInorder();


    // --------------------------------------------------------
    // HASH TABLE
    // --------------------------------------------------------

    std::cout
        << "\n--- HASH TABLE ---\n";

    playerTable.display();


    // ========================================================
    // STEP 9 — FINAL EXPLANATION
    // ========================================================

    std::cout
        << "\n\n============================================\n";

    std::cout
        << "             PHASE 1 COMPLETE\n";

    std::cout
        << "============================================\n";

    std::cout
        << "\nQueue       -> manages waiting order\n";

    std::cout
        << "Priority Q  -> manages waiting priority\n";

    std::cout
        << "Hash Table  -> fast player ID lookup\n";

    std::cout
        << "AVL Tree    -> skill-based candidate search\n";

    std::cout
        << "Matchmaking -> compatibility calculation\n";

    std::cout
        << "Match       -> stores final matched players\n";


    return 0;
}