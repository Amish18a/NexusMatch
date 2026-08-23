#ifndef AVLTREE_H
#define AVLTREE_H

#include "Player.h"

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
        void inorderTraversal(Node* node) const;
        void destroyTree(Node* node);

        Node* searchSkillRange(Node* node,int targetSkill,int tolerance) const;
    public:
        AVLTree();
        ~AVLTree();
        void insert(const Player& player);
        void displayInorder() const;
        Player* findClosestPlayer(int targetSkill,int tolerance) const;    
};

#endif