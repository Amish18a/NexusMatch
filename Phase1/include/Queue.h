#ifndef QUEUE_H
#define QUEUE_H

#include "Player.h"

class PlayerQueue
{
    private:
        Player* players;
        
        int capacity , front , rear, size;
    public:
        PlayerQueue(int capacity);
        
        ~PlayerQueue();

        bool isEmpty() const;
        bool isFull() const;
        
        void enqueue(const Player& player);
        Player dequeue();

        Player& getFront();

        int getSize() const;

        void display() const;
        bool removePlayer(int playerId);
};

#endif