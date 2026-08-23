#include <iostream>
#include "../include/Player.h"
#include "../include/Queue.h"

int main()
{
    Player p1(101,"Amish",1520,"India","Ranked",42,94);
    Player p2(102,"Gurveer",1490,"India","Ranked",38,91);
    Player p3(103,"Ruya",1520,"India","Ranked",51,97);

    PlayerQueue matchmakingQueue(5);

    matchmakingQueue.enqueue(p1);
    matchmakingQueue.enqueue(p2);
    matchmakingQueue.enqueue(p3);

    matchmakingQueue.display();

    std::cout << "\nRemoving first player...\n";
    Player removedPlayer = matchmakingQueue.dequeue();
    std::cout << "Removed: "
              << removedPlayer.getName()
              << '\n';

    matchmakingQueue.display();
    return 0;
}