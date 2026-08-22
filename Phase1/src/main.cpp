#include <iostream>
#include "../include/Player.h"

int main()
{
    Player p1(101,"Amish",1520,"India","Ranked",42,94);
    Player p2(102,"Gurveer",1490,"India","Ranked",38,91);
    Player p3(103,"Ruya",1520,"India","Ranked",51,97);

    p1.setWaiting(true);
    p2.setWaiting(true);
    p3.setWaiting(true);

    p1.setWaitingTime(18);
    p2.setWaitingTime(25);
    p3.setWaitingTime(10);
    
    p1.display();
    p2.display();
    p3.display();

    return 0;
}