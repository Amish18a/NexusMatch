#include <iostream>
#include "../include/Player.h"
#include "../include/AVLTree.h"
#include "../include/MatchmakingEngine.h"

int main()
{
    Player amish(101,"Amish",1520,"India","Ranked",42,94);
    Player gurveer(102,"Gurveer",1490,"India","Ranked",38,91);
    Player riya(103,"Riya",1520,"India","Ranked",51,97);

    Player player4(104,"Player4",1515,"India","Ranked",120,88);
    Player player5(105,"Player5",1800,"India","Ranked",35,99);
    
    amish.setWaitingTime(20);

    AVLTree skillTree;

    skillTree.insert(amish);
    skillTree.insert(gurveer);
    skillTree.insert(riya);
    skillTree.insert(player4);
    skillTree.insert(player5);
    skillTree.displayInorder();
    MatchmakingEngine matchmaking;

    Player matchedPlayer;

    bool found = matchmaking.findMatch(amish,skillTree,matchedPlayer);

    if (found)
    {
        std::cout << "\n===== MATCH FOUND ========\n";

        std::cout
            << amish.getName()
            << "matched with "
            << matchedPlayer.getName()
            <<'\n';
        std::cout << "==================================\n";

    }
    else
    {
        std::cout   
            <<"\n No suitable match found.\n";
    }
    return 0;
}