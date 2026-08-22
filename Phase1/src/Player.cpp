#include "../include/Player.h"
#include <iostream>

Player::Player()
{
    playerId=0;
    name="";
    skillRating=0;
    region="";
    gamemode="";

    ping=0;
    waitingTime=0;
    trustScore=100;

    waiting=false;
}

Player::Player(int id,const std::string& playerName,int skill,
    const std::string& playerRegion,const std::string& mode,
    int playerPing,int trust){
        playerId=id;
        name=playerName;
        skillRating=skill;
        region=playerRegion;
        gamemode=mode;

        ping=playerPing;
        waitingTime=0;
        trustScore=trust;

        waiting=false;
    }
int Player::getId() const
{
    return playerId;
}
std::string Player::getName() const
{
    return name;
}
int Player::getSkill() const
{
    return skillRating;
}
std::string Player::getRegion() const
{
    return region;
}
std::string Player::getGameMode() const
{
    return gamemode;
}
int Player::getPing() const
{
    return ping;
}
int Player::getWaitingTime() const
{
    return waitingTime;
}
int Player::getTrustScore() const
{
    return trustScore;
}
bool Player::isWaiting() const
{
    return waiting;
}
void Player::setPing(int newPing)
{
    ping = newPing;
}
void Player::setWaitingTime(int time)
{
    waitingTime=time;
}
void Player::setTrustScore(int score)
{
    trustScore = score;
}
void Player::setWaiting(bool status)
{
    waiting=status;
}

void Player::display() const 
{
    std::cout << "\n-----------------------------\n";

    std::cout << "Player ID      : " << playerId << '\n';
    std::cout << "Name           : " << name << '\n';
    std::cout << "Skill Rating   : " << skillRating << '\n';
    std::cout << "Region         : " << region << '\n';
    std::cout << "Game Mode      : " << gamemode << '\n';
    std::cout << "Ping           : " << ping << " ms\n";
    std::cout << "Waiting Time   : " << waitingTime << " sec\n";
    std::cout << "Trust Score    : " << trustScore << '\n';

    std::cout << "Status         : " 
              << (waiting ? "WAITING" : "NOT WAITING")
              <<'\n';

    std::cout << "\n-----------------------------\n";
}