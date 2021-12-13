# StarCraft 2 Tournament Elo

## 1. Tournaments Data

Criteria
- Legacy of the Void (LotV)
- Ended between 2016/01/01 - 2021/12/12 (as of now)
- Open bracket, group stage, playoffs

Statistics (as of now)
- 110 premier events
- 236 major events
- 13,176 matches (1 match = 1 complete Best-of-N)
- 38,257 maps
- 692 pro-players

## 2. Elo System

The vanilla Elo system
- Logistic distribution; 400 higher in rating corresponds to a 10:1 odds for winning
- Every new player receives an initial rating of 1500
- Each match: the winner's rating gain equals the loser's rating loss
- The gain is proportional to the probability of losing
- The gain is scaled to +0\~20 for players with >= 50 matches; +0\~40 otherwise
- Ratings are updated after each tournament

## 3. Ranking Results

https://tinyurl.com/sc2-tournament-elo

- The tables show those dominant players whose ratings >= 1600 and #match >= 20
- Two tabs rank players respectively by current ratings and highest career ratings
- A total of 100/154 dominant players (current ratings / highest ratings) (as of now)
- Players' races are shown as the races they use most frequently
- The tables also contain players' rating changes in the past 180 days
- 7 players have once achieved 2000+ ratings (as of now)
