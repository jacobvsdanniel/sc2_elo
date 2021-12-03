# StarCraft 2 Tournament Elo

## 1. Tournaments Data

Criteria
- Legacy of the Void (LotV)
- Ended between 2016/01/01 - 2021/11/30 (as of now)
- Open bracket, group stage, playoffs

Statistics (as of now)
- 107 premier events
- 231 major events
- 12,889 matches (1 match = 1 complete Best-of-N)
- 37,378 maps
- 685 pro-players

## 2. Elo System

The vanilla Elo system
- Logistic distribution; a 400 rating difference equals 10 times winning odds difference
- Every new player receives an initial rating of 1500
- Each match: the winner's rating gain equals the loser's rating loss
- The gain is inversely proportional to the winning-losing odds ratio
- The gain is scaled to +0\~20 for players with >= 50 matches; +0\~40 otherwise
- Ratings are updated after each tournament

## 3. Ranking Results

https://tinyurl.com/sc2-tournament-elo

- The table shows those players whose rating >= 1600 and #match >= 20
- A total of 99 dominant players are on the list (as of now)
- Players' races are shown as the races they use most frequently
- The table also contains players' highest rating and rating changes in the past 60 days
- 4 players have once achieved 2000+ ratings (as of now)
