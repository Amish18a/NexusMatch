#ifndef HASHTABLE_H
#define HASHTABLE_h

#include "Player.h"

class HashTable
{
    private:
        struct Node
        {
            Player player;
            Node* next;
            Node(const Player& p)
            {
                player=p;
                next=nullptr;
            }
        };
        Node** table;
        int capacity;
        int hashFunction(int playerId) const;
    public:
        HashTable(int size);
        ~HashTable();

        void insert(const Player& player);

        Player* search(int playerId);

        bool remove(int playerId);

        void display() const;
};

#endif