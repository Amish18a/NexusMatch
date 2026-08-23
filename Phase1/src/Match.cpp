#include "../include/Match.h"
#include <iostream>

Match::Match(int id, int requiredPlayers)
{
    matchId = id;
    this->requiredPlayers = requiredPlayers;
}

bool Match::addPlayer(const Player& player)
{
    if (isFull())
    {
        return false;
    }

    players.push_back(player);

    return true;
}

bool Match::isFull() const
{
    return players.size() >= requiredPlayers;
}

int Match::getMatchId() const
{
    return matchId;
}

int Match::getPlayerCount() const
{
    return players.size();
}

void Match::display() const
{
    std::cout << "\n========== MATCH ==========\n";

    std::cout << "Match ID: "
              << matchId
              << '\n';

    std::cout << "Players: "
              << players.size()
              << " / "
              << requiredPlayers
              << "\n\n";

    for (int i = 0; i < players.size(); i++)
    {
        std::cout
            << i + 1
            << ". "
            << players[i].getName()
            << " | Skill: "
            << players[i].getSkill()
            << '\n';
    }

    if (isFull())
    {
        std::cout << "\nStatus: FULL\n";
    }
    else
    {
        std::cout << "\nStatus: WAITING\n";
    }

    std::cout << "===========================\n";
}