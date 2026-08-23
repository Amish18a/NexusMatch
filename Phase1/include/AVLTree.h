#ifndef AVLTREE_H
#define AVLTREE_H

#include "Player.h"
#include<vector>

class AVLTree
{
    private:
        struct Node
        {
            Player player;

            Node* left;
            Node* right;
            int height;

            Node(const Player& p)
            {
                player = p;
                left = nullptr;
                right = nullptr;
                height = 1;
            }
        };
        Node* root;
        int getHeight(Node* node) const;
        int getBalanceFactor(Node* node) const;
        int getMax(int a,int b) const;
        Node* rightRotate(Node* y);
        Node* leftRotate(Node* x);
        Node* insertNode(Node* node,const Player& player);
        Node* deleteNode(Node* node, int skill, int playerId);
        Node* getMinValueNode(Node* node);
        void inorderTraversal(Node* node) const;
        void destroyTree(Node* node);
        void collectRange(Node* node,int minSkill,int maxSkill,std::vector<Player>& candidates) const;

        Node* searchSkillRange(Node* node,int targetSkill,int tolerance) const;
    public:
        AVLTree();
        ~AVLTree();
        void insert(const Player& player);
        void remove(const Player& player);
        void displayInorder() const;
        Player* findClosestPlayer(int targetSkill,int tolerance) const;    
        void getPlayersInRange(int minSkill,int maxSkill,std::vector<Player>& candidates) const;
};

#endif