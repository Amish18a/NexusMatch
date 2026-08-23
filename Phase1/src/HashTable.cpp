#include "../include/HashTable.h"
#include<iostream>

HashTable::HashTable(int size)
{
    capacity = size;
    table = new Node*[capacity];
    int i;
    for (i=0;i<capacity;i++)
    {
        table[i] = nullptr;
    }
}

HashTable::~HashTable()
{
    int i;
    for (i=0;i<capacity;i++)
    {
        Node* current = table[i];

        while(current != nullptr)
        {
            Node* temp = current;
            current = current->next;
            delete temp;
        }
    }
    delete[] table;
}

int HashTable::hashFunction(int playerId) const
{
    return playerId % capacity;
}

void HashTable::insert(const Player& player)
{
    int index = hashFunction(player.getId());

    Node* newNode = new Node(player);
    
    if(table[index] == nullptr)
    {
        table[index] = newNode;
    }
    else
    {
        Node* current = table[index];

        while (current->next != nullptr)
        {
            current = current ->next;
        }
        current->next = newNode;
    }
    std::cout << "Player "
              << player.getId()
              <<" inserted at index "
              << index 
              << ".\n";   
}

Player* HashTable::search(int playerId)
{
    int index = hashFunction(playerId);
    Node* current = table[index];
    while (current != nullptr)
    {
        if (current->player.getId() == playerId)
        {
            return &(current->player);
        }
        current = current->next;
    }
    return nullptr;    
}

bool HashTable::remove(int playerId)
{
    int index = hashFunction(playerId);
    Node* current = table[index];
    Node* previous = nullptr;

    while (current != nullptr)
    {
        if (current->player.getId() == playerId)
        {
            if (previous == nullptr)
            {
                table[index] = current->next;
            }
            else
            {
                previous->next = current->next;
            }
            delete current;
            return true;
        }
        previous = current;
        current = current->next;
    }
    return false;
}

void HashTable::display() const
{
    std::cout << "\n =========== HASH TABLE ===========\n";

    int i;
    for(i=0;i<capacity;i++)
    {
        std::cout << "Index " << i << ": ";
        Node* current =table[i];
        if(current == nullptr)
        {
            std::cout << "EMPTY";
        }
        while (current != nullptr)
        {
            std::cout << current->player.getId();

            if (current->next != nullptr)
            {
                std::cout << "->";
            }
            current  = current->next;
        }
        std::cout << '\n';
    }
    std::cout << "===================================\n";
}
