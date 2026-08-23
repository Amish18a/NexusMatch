#include "../include/Queue.h"
#include <iostream>

PlayerQueue::PlayerQueue(int queueCapacity)
{
    capacity=queueCapacity;

    players = new Player[capacity];

    front=0;
    rear=-1;
    size=0;
}

PlayerQueue::~PlayerQueue()
{
    delete[] players;
}

bool PlayerQueue::isEmpty() const
{
    return size == 0;
}

bool PlayerQueue::isFull() const
{
    return size == capacity;
}

void PlayerQueue::enqueue(const Player& player)
{
    if (isFull())
    {
        std::cout << "Queue is full. Player cannot join.\n";
        return ;
    }

    rear = (rear+1)% capacity;
    players[rear] = player;
    size++;
    std::cout << player.getName()
              << "Joined the matchmaking queue.\n";
}
Player PlayerQueue::dequeue()
{
    if (isEmpty())
    {
        std::cout << "Queue is empty.\n";
        return Player();
    }
    Player player = players[front];
    front = (front+1)%capacity;
    size--;
    return player;
}

Player& PlayerQueue::getFront()
{
    return players[front];
}

int PlayerQueue::getSize() const
{
    return size;
}

void PlayerQueue::display() const
{
    if (isEmpty())
    {
        std::cout << "Matchmaking queue is empty.\n";
        return;
    }

    std::cout << "\n===== MATCHMAKING QUEUE =====\n";

    int index = front,i;

    for(i=0;i<size;i++)
    {
        std::cout << "Player "
                  << players[index].getId()
                  << " | "
                  << players[index].getName()
                  << " | Skill: "
                  << players[index].getSkill()
                  << '\n';
        index=(index+1)%capacity;
    }
    std::cout << "============================================\n";
}