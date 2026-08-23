#ifndef PRIORITYQUEUE_H
#define PRIORITYQUEUE_H

#include "Player.h"

class PriorityQueue
{
private:

    struct PriorityNode
    {
        Player player;
        int priority;

        PriorityNode* next;

        PriorityNode(
            const Player& p,
            int pr
        )
            : player(p),
              priority(pr),
              next(nullptr)
        {
        }
    };

    PriorityNode* head;

    int size;

public:

    PriorityQueue();

    ~PriorityQueue();

    bool isEmpty() const;

    void enqueue(
        const Player& player,
        int priority
    );

    Player dequeue();

    Player& getHighestPriority();

    int getSize() const;

    void display() const;
};

#endif