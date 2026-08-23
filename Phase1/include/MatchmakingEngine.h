#ifndef MATCHMAKINGENGINE_H
#define MATCHMAKINGENGINE_H
#include "Player.h"
#include "AVLTree.h"
class MatchmakingEngine
{
    private:
        double calculateSkillScore(const Player& player,const Player& candidate) const;

        double calculatePingScore(const Player& player,const Player& candidate) const;

        double calculateTrustScore(const Player& player,const Player& candidate) const;

        double calculateWaitingScore(const Player& player) const;

        double calculateCompatibilityScore(const Player& player,const Player& candidate) const;
        
        bool isBasicCompatible(const Player& player,const Player& candidate) const;
    public:
        MatchmakingEngine();
        bool findMatch(const Player& player,AVLTree& skillTree,Player& matchedPlayer) const;
};
#endif