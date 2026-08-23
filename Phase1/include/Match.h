#ifndef MATCH_H
#define MATCH_H

#include <vector>
#include "Player.h"

class Match
{
private:
    int matchId;
    int requiredPlayers;
    std::vector<Player> players;

public:
    Match(int id, int requiredPlayers);

    bool addPlayer(const Player& player);

    bool isFull() const;

    int getMatchId() const;

    int getPlayerCount() const;

    void display() const;
};

#endif