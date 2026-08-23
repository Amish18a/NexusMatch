#include "../include/MatchmakingEngine.h"
#include <cmath>
#include <iostream>
#include <vector>

bool MatchmakingEngine::isBasicCompatible(const Player& player,const Player& candidate)const
{
    if(player.getId() == candidate.getId())
    {
        return false;
    }
    if (player.getRegion()!=candidate.getRegion())
    {
        return false;
    }
    if (player.getGameMode() != candidate.getGameMode())
    {
        return false;
    }
    return true;
}

double MatchmakingEngine::calculateSkillScore(const Player& player,const Player& candidate)const
{
    int difference = std::abs(player.getSkill() - candidate.getSkill());
    double score = 100.0 -(difference/5.0);
    if(score<0)
    {
        score = 0;
    }
    return score;
}

double MatchmakingEngine::calculatePingScore(const Player& player,const Player& candidate) const 
{
    int difference = std::abs(player.getPing() - candidate.getPing());
    double score =100.0 -difference;
    if (score<0)
    {
        score = 0;
    }
    return score;
}

double MatchmakingEngine::calculateTrustScore(const Player& player,const Player& candidate) const 
{
    int difference =std::abs(player.getTrustScore() - candidate.getTrustScore());
    double score = 100.0 - difference;
    if (score<0)
    {
        score =0;
    }
    return score;
}

double MatchmakingEngine::calculateWaitingScore(const Player& player) const
{
    int waitingTime = player.getWaitingTime();
    if(waitingTime>100)
    {
        waitingTime =100;
    }
    return waitingTime;
}

double MatchmakingEngine::calculateCompatibilityScore(const Player& player,const Player& candidate) const
{
    double skillScore=calculateSkillScore(player,candidate);
    double pingScore=calculatePingScore(player,candidate);
    double trustScore=calculateTrustScore(player,candidate);
    double waitingScore=calculateWaitingScore(player);
    double finalScore =(skillScore * 0.50)+ (pingScore * 0.20)+ (trustScore * 0.20)+ (waitingScore * 0.10);
    return finalScore;
}

MatchmakingEngine::MatchmakingEngine()
{
}

bool MatchmakingEngine::findMatch(
    const Player& player,
    AVLTree& skillTree,
    Player& matchedPlayer
) const
{
    int tolerance = 100;

    int minSkill =
        player.getSkill() - tolerance;

    int maxSkill =
        player.getSkill() + tolerance;

    std::vector<Player> candidates;

    skillTree.getPlayersInRange(
        minSkill,
        maxSkill,
        candidates
    );

    bool found = false;
    double bestScore = -1.0;

    for (const Player& candidate : candidates)
    {
        // Do not match the player with themselves
        if (player.getId() == candidate.getId())
        {
            continue;
        }

        // Check region compatibility
        if (player.getRegion() != candidate.getRegion())
        {
            continue;
        }

        // Check game mode compatibility
        if (player.getGameMode() != candidate.getGameMode())
        {
            continue;
        }

        // Calculate individual scores
        double skillScore =
            calculateSkillScore(
                player,
                candidate
            );

        double pingScore =
            calculatePingScore(
                player,
                candidate
            );

        double trustScore =
            calculateTrustScore(
                player,
                candidate
            );

        double waitingScore =
            calculateWaitingScore(
                player
            );

        // Calculate final compatibility score
        double finalScore =
              (skillScore * 0.50)
            + (pingScore * 0.20)
            + (trustScore * 0.20)
            + (waitingScore * 0.10);

        // Select the best candidate
        if (!found || finalScore > bestScore)
        {
            bestScore = finalScore;
            matchedPlayer = candidate;
            found = true;
        }
    }

    return found;
}