#ifndef PLAYER_H
#define PLAYER_H

#include <string>

class Player
{
    private:
        int playerId,skillRating,ping,waitingTime,trustScore;
        std::string name,region,gamemode;
        bool waiting;
    public:
        Player();


        Player(int id,const std::string& playerName,int skill
        ,const std::string& playerRegion,const std::string& mode,
        int playerPing,int trust);


        int getId() const;
        std::string getName() const;
        int getSkill() const;
        std::string getRegion() const;
        std::string getGameMode() const;

        int getPing() const;
        int getWaitingTime() const;
        int getTrustScore() const;

        bool isWaiting() const;

        void setPing(int newPing);
        void setWaitingTime(int time);
        void setTrustScore(int score);
        void setWaiting(bool status);

        void display() const;
};

#endif