# StarCraft 2 Tournament Elo

## 1. Tournaments Data

Criteria
- Legacy of the Void (LotV)
- Ended between 2016/01/01 - 2021/12/31 (as of now)
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

- Two tables rank players respectively by current ratings and highest career ratings
- The tables also contain players' rating changes in the past 180 days
- Players' races are shown as the races they use most frequently
- To be listed, a player must have a rating >= 1600 and #match >= 20
- For the current ratings table only: To be listed, a player must have rating changes in the past 180 days
- A total of 67/154 dominant players (current ratings / highest ratings) (as of now)
- 7 players have once achieved 2000+ ratings (as of now)
