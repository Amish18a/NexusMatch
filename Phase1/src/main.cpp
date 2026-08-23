#include <iostream>
#include "../include/Player.h"
#include "../include/AVLTree.h"

int main()
{
    Player p1(101,"Amish",1520,"India","Ranked",42,94);
    Player p2(102,"Gurveer",1490,"India","Ranked",38,91);
    Player p3(103,"Ruya",1520,"India","Ranked",51,97);

    Player p4(111, "Player4", 1480, "India", "Ranked", 45, 90);
    Player p5(121, "Player5", 1500, "India", "Ranked", 49, 93);
    Player p6(106, "Player6", 1300, "India", "Ranked", 55, 89);

    AVLTree skillTree;

    skillTree.insert(p1);
    skillTree.insert(p2);
    skillTree.insert(p3);
    skillTree.insert(p4);
    skillTree.insert(p5);
    skillTree.insert(p6);

    skillTree.displayInorder();

    std::cout << "\nSearching for player near skill 1520...\n";

    Player* result = skillTree.findClosestPlayer(2000,50);

    if (result != nullptr)
    {
        result->display();
    }
    else
    {
        std::cout << "No suitable player found.\n";
    }
    return 0;
}