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

void AVLTree::remove(const Player& player)
{
    root =
        deleteNode(
            root,
            player.getSkill(),
            player.getId()
        );
}

AVLTree::Node* AVLTree::getMinValueNode(Node* node)
{
    Node* current = node;

    while (current->left != nullptr)
    {
        current = current->left;
    }

    return current;
}
AVLTree::Node* AVLTree::deleteNode(
    Node* node,
    int skill,
    int playerId
)
{
    if (node == nullptr)
    {
        return nullptr;
    }

    int currentSkill =
        node->player.getSkill();

    int currentId =
        node->player.getId();

    // Search for the player
    if (skill < currentSkill)
    {
        node->left =
            deleteNode(
                node->left,
                skill,
                playerId
            );
    }
    else if (skill > currentSkill)
    {
        node->right =
            deleteNode(
                node->right,
                skill,
                playerId
            );
    }
    else
    {
        // Same skill found
        // Check player ID because
        // multiple players can have same skill
        if (playerId < currentId)
        {
            node->left =
                deleteNode(
                    node->left,
                    skill,
                    playerId
                );
        }
        else if (playerId > currentId)
        {
            node->right =
                deleteNode(
                    node->right,
                    skill,
                    playerId
                );
        }
        else
        {
            // Player found

            // Case 1: no child
            if (node->left == nullptr &&
                node->right == nullptr)
            {
                delete node;
                return nullptr;
            }

            // Case 2: only right child
            if (node->left == nullptr)
            {
                Node* temp = node->right;

                delete node;

                return temp;
            }

            // Case 3: only left child
            if (node->right == nullptr)
            {
                Node* temp = node->left;

                delete node;

                return temp;
            }

            // Case 4: two children
            Node* successor =
                getMinValueNode(node->right);

            node->player =
                successor->player;

            node->right =
                deleteNode(
                    node->right,
                    successor->player.getSkill(),
                    successor->player.getId()
                );
        }
    }

    // Update height
    node->height =
        1 + getMax(
            getHeight(node->left),
            getHeight(node->right)
        );

    // Check balance
    int balance =
        getBalanceFactor(node);

    // LL
    if (balance > 1 &&
        getBalanceFactor(node->left) >= 0)
    {
        return rightRotate(node);
    }

    // LR
    if (balance > 1 &&
        getBalanceFactor(node->left) < 0)
    {
        node->left =
            leftRotate(node->left);

        return rightRotate(node);
    }

    // RR
    if (balance < -1 &&
        getBalanceFactor(node->right) <= 0)
    {
        return leftRotate(node);
    }

    // RL
    if (balance < -1 &&
        getBalanceFactor(node->right) > 0)
    {
        node->right =
            rightRotate(node->right);

        return leftRotate(node);
    }

    return node;
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