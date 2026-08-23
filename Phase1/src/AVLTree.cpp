#include"../include/AVLTree.h"
#include <iostream>
#include<cstdlib>

AVLTree::AVLTree()
{
    root = nullptr;
}

AVLTree::~AVLTree()
{
    destroyTree(root);
}

int AVLTree::getHeight(Node* node) const
{
    if (node==nullptr)
    {
        return 0;
    }

    return node->height;
}

int AVLTree::getMax(int a,int b) const
{
    return (a>b)? a:b;
}
int AVLTree::getBalanceFactor(Node* node) const
{
    if (node ==nullptr)
    {
        return 0;
    }
    return getHeight(node->left)
         - getHeight(node->right);
}

AVLTree::Node* AVLTree::rightRotate(Node* y)
{
    Node* x = y->left;
    Node* temp  = x->right;
    x->right =y;
    y->left =temp;
    y->height = 1+ getMax(getHeight(y->left),getHeight(y->right));
    x->height = 1+ getMax(getHeight(x->left),getHeight(x->right));
    return x;
}

AVLTree::Node* AVLTree::leftRotate(Node* x)
{
    Node* y=x->right;
    Node* temp = y->left;
    y->left = x;
    x->right =temp;
    x->height = 1+getMax(getHeight(x->left),getHeight(x->right));
    y->height = 1+getMax(getHeight(y->left),getHeight(y->right));

    return y;
}

AVLTree::Node* AVLTree::insertNode(Node* node,const Player& player)
{
    if (node==nullptr)
    {
        return new Node(player);
    }

    int currentSkill= node->player.getSkill();
    int newSkill = player.getSkill();

    if(newSkill<currentSkill)
    {
        node->left = insertNode(node->left,player);
    }
    else if (newSkill>currentSkill)
    {
        node->right = insertNode(node->right,player);
    }
    else
    {
        if(player.getId() < node->player.getId())
        {
            node->left  = insertNode(node->left,player);
        }
        else{
            node->right = insertNode(node->right,player);
        }
    }
    node->height=1+getMax(getHeight(node->left),getHeight(node->right));
    int balance = getBalanceFactor(node);

    //LL
    if (balance>1 && newSkill<node->left->player.getSkill())
    {
        return rightRotate(node);
    }
    //RR
    if(balance<-1 && newSkill>node->right->player.getSkill())
    {
        return leftRotate(node);
    }
    //LR
    if(balance>1 && newSkill>node->left->player.getSkill())
    {
        node->left = leftRotate(node->left);
        return rightRotate(node);
    }
    //RL
    if(balance<-1 && newSkill<node->right->player.getSkill())
    {
        node->right = rightRotate(node->right);
        return leftRotate(node);
    }
    return node;
}

void AVLTree::insert(const Player& player)
{
    root = insertNode(root,player);
}

void AVLTree::inorderTraversal(Node* node) const
{
    if (node == nullptr)
    {
        return ;
    }
    inorderTraversal(node->left);

    std::cout
        << "Player ID: "
        << node->player.getId()
        <<" | Name: "
        << node->player.getName()
        <<" | Skill: "
        << node->player.getSkill()
        <<'\n';
    inorderTraversal(node->right);
}

void AVLTree::displayInorder() const
{
    std::cout << "\n============= AVL TREE =============\n";

    inorderTraversal(root);

    std::cout << "=======================================\n";
}
void AVLTree::destroyTree(Node* node)
{
    if (node == nullptr)
    {
        return;
    }
    destroyTree(node->left);
    destroyTree(node->right);

    delete node;
}

AVLTree::Node* AVLTree::searchSkillRange(Node* node,int targetSkill,int tolerance) const
{
    if (node == nullptr)
    {
        return nullptr;
    }
    int skill = node->player.getSkill();
    if (skill >= targetSkill -tolerance && skill<= targetSkill + tolerance)
    {
        return node;
    }
    if (skill>targetSkill)
    {
        return searchSkillRange(node->left,targetSkill,tolerance);    
    }
    return searchSkillRange(node->right,targetSkill,tolerance);
}

Player* AVLTree::findClosestPlayer(int targetSkill,int tolerance) const 
{
    Node* result = searchSkillRange(root,targetSkill,tolerance);
    if (result == nullptr)
    {
        return nullptr;
    }
    return &(result->player);
}

void AVLTree::collectRange(
    Node* node,
    int minSkill,
    int maxSkill,
    std::vector<Player>& candidates
) const
{
    if (node == nullptr)
    {
        return;
    }

    int skill = node->player.getSkill();

    // Check current node
    if (skill >= minSkill && skill <= maxSkill)
    {
        candidates.push_back(node->player);
    }

    // Search left subtree
    if (skill >= minSkill)
    {
        collectRange(
            node->left,
            minSkill,
            maxSkill,
            candidates
        );
    }

    // Search right subtree
    if (skill <= maxSkill)
    {
        collectRange(
            node->right,
            minSkill,
            maxSkill,
            candidates
        );
    }
}

void AVLTree::getPlayersInRange(int minSkill,int maxSkill,std::vector<Player>& candidates) const
{
    collectRange(root,minSkill,maxSkill,candidates);
}