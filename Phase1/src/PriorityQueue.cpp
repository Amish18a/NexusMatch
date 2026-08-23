#include "../include/PriorityQueue.h"
#include <stdexcept>
#include <iostream>

PriorityQueue::PriorityQueue()
{
    head = nullptr;
    size = 0;
}

PriorityQueue::~PriorityQueue()
{
    while (!isEmpty())
    {
        dequeue();
    }
}

bool PriorityQueue::isEmpty() const
{
    return head == nullptr;
}
void PriorityQueue::enqueue(
    const Player& player,
    int priority
)
{
    PriorityNode* newNode =
        new PriorityNode(
            player,
            priority
        );

    // Empty queue
    if (head == nullptr)
    {
        head = newNode;
        size++;
        return;
    }

    // Highest priority comes first
    if (priority > head->priority)
    {
        newNode->next = head;
        head = newNode;
        size++;
        return;
    }

    PriorityNode* current = head;

    while (
        current->next != nullptr &&
        current->next->priority >= priority
    )
    {
        current = current->next;
    }

    newNode->next = current->next;

    current->next = newNode;

    size++;
}
Player PriorityQueue::dequeue()
{
    if (isEmpty())
    {
        throw std::runtime_error(
            "Priority Queue is empty."
        );
    }

    PriorityNode* temp = head;

    Player player = head->player;

    head = head->next;

    delete temp;

    size--;

    return player;
}
Player& PriorityQueue::getHighestPriority()
{
    if (isEmpty())
    {
        throw std::runtime_error(
            "Priority Queue is empty."
        );
    }

    return head->player;
}
int PriorityQueue::getSize() const
{
    return size;
}
void PriorityQueue::display() const
{
    std::cout
        << "\n===== WAITING PRIORITY QUEUE =====\n";

    PriorityNode* current = head;

    while (current != nullptr)
    {
        std::cout
            << "Player ID: "
            << current->player.getId()
            << " | Name: "
            << current->player.getName()
            << " | Waiting Priority: "
            << current->priority
            << '\n';

        current = current->next;
    }

    std::cout
        << "===================================\n";
}