#include <iostream>
#include "../include/Player.h"
#include "../include/Hashtable.h"

int main()
{
    Player p1(101,"Amish",1520,"India","Ranked",42,94);
    Player p2(102,"Gurveer",1490,"India","Ranked",38,91);
    Player p3(103,"Ruya",1520,"India","Ranked",51,97);

    Player p4(111, "Player4", 1480, "India", "Ranked", 45, 90);
    Player p5(121, "Player5", 1500, "India", "Ranked", 49, 93);

    HashTable players(10);

    players.insert(p1);
    players.insert(p2);
    players.insert(p3);
    players.insert(p4);
    players.insert(p5);

    players.display();

    std::cout << "\nSearching for Player Id 121...\n";

    Player* result = players.search(121);

    if(result!=nullptr)
    {
        result->display();
    }
    else 
    {
        std::cout << "Player not found.\n";
    }
    return 0;
}