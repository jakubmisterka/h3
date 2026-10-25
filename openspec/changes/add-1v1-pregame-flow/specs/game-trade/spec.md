# Spec Delta

## Purpose

Covers the trade that players do before each game: rolling and banning towns, bidding gold for the town choice and for color. The bot guides the sections, keeps the gold, and posts the final lobby settings.

## ADDED Requirements

### Requirement: Each game has its own trade, one open at a time
A game's trade SHALL be able to start as soon as the game's template is known: a game that has been picked, or the decider's game once the bans and picks are done. This SHALL be possible while selection is still going on. A player starts a trade by naming the game (its number) or its template; without a name the bot SHALL take the first known game whose trade is not finished. Only one trade SHALL be open at a time. Starting a trade SHALL close the open one, which keeps what was recorded and counts as incomplete. Starting a trade that was started before SHALL reopen it where it stopped, with the same town pair and gold. Reports, rolls, declines and undo SHALL act on the open trade. A trade that is finished SHALL NOT be started again. Each game's trade SHALL start from its own starting gold; nothing carries over between games.

#### Scenario: Start while selection goes on
- **WHEN** A has picked JC in a best-of-3 and the bans and picks are not done
- **THEN** a player can start the trade of game 1, and the trade begins with the template, the gold and the first section

#### Scenario: Game not known yet
- **WHEN** a player starts the trade of the decider's game while bans and picks are still going
- **THEN** the bot refuses and says the template is not decided yet

#### Scenario: Continue later
- **WHEN** the trade of game 1 is done and players come back next day
- **THEN** starting a trade without a name offers game 2, and game 1 stays finished

#### Scenario: Naming the game by its template
- **WHEN** a player starts a trade naming Jebus Cross, which is game 2
- **THEN** the trade of game 2 is opened

#### Scenario: Opening a second trade
- **WHEN** the trade of game 1 is open and a player starts the trade of game 2
- **THEN** game 1's trade is closed as incomplete and game 2's trade is the open one, and the bot says so

#### Scenario: Reopening a trade
- **WHEN** a player starts the trade of game 1 again after opening game 2
- **THEN** game 1's trade continues where it stopped, with the same pair and the same gold, and game 2's trade is closed as incomplete

#### Scenario: No open trade
- **WHEN** a player reports a result and no trade is open
- **THEN** the bot refuses and says to start a trade first

#### Scenario: Finished trade
- **WHEN** a player starts the trade of a game that is finished
- **THEN** the bot refuses and says it is finished

#### Scenario: Several trades in the overview
- **WHEN** a player asks for the status of the match
- **THEN** the bot lists the next selection step and every started trade with its section and gold, and marks the open one

### Requirement: The trade runs in sections
The trade of a game SHALL run in sections in a fixed order: town roll, town bid, color bid. Each section starts with a bot message that says what to do, who starts and the minimum raise (100 gold). The bot SHALL not accept a result for a section until the sections before it are done.

#### Scenario: Prompting
- **WHEN** a trade starts
- **THEN** the bot posts the template, each player's starting gold, and the first section's instruction (for the roll section, the generated pair, the roll cost and who may roll)

#### Scenario: Out of order
- **WHEN** a player reports a color bid before the town bid is done
- **THEN** the bot refuses and names the section that is expected

### Requirement: The bot generates the town pair
When the roll section starts, the bot SHALL draw two different towns at random, each allowed town equally likely, and announce in the thread the pair, the roll cost, and which players may roll (the first player, the second player, or both). A player may roll only if they have a roll left and enough gold for the cost. Players set the announced towns in the lobby by hand.

#### Scenario: Announcement
- **WHEN** the roll section starts for a 160% game with default roll rules
- **THEN** the thread says, for example, "Castle vs Factory. A roll costs 500 gold. Both players may roll."

#### Scenario: Only one player may roll
- **WHEN** the roll cost is more than one player's gold
- **THEN** the announcement names only the other player as eligible

#### Scenario: Nobody may roll
- **WHEN** neither player has a roll left or enough gold
- **THEN** the roll section ends at once and the town bid starts

#### Scenario: Fair draw
- **WHEN** many pairs are drawn from the same allowed towns
- **THEN** every allowed town appears equally often, and a pair never repeats one town

### Requirement: A roll costs gold and draws a new pair
An eligible player SHALL be able to roll by naming the towns to ban (0 up to the allowed maximum), from the current pair. The roller SHALL pay the roll cost to the opponent. The bot SHALL then draw a new pair of two different towns from the allowed towns that are not banned, and announce the new pair, the roll cost, and who may still roll.

#### Scenario: One roll
- **WHEN** the pair is Castle vs Factory and P1 rolls banning Castle
- **THEN** P1 pays 500 gold to P2, the bot draws a new pair without Castle (for example Necropolis vs Tower), and announces that P2 may still roll

#### Scenario: Roll without bans
- **WHEN** a player rolls banning nothing
- **THEN** they pay the cost and the bot draws a new pair

#### Scenario: Too many bans
- **WHEN** a player names more bans than allowed, or a town that is not in the current pair
- **THEN** the bot refuses, states the limit, and nobody pays

#### Scenario: Not eligible
- **WHEN** a player who has no roll left or cannot pay tries to roll
- **THEN** the bot refuses and says why

#### Scenario: Too few towns left
- **WHEN** fewer than two allowed towns remain after the bans
- **THEN** the bot refuses the roll and nobody pays

### Requirement: Each eligible player rolls or declines
The roll section SHALL end when every eligible player has rolled all their rolls or declined. A player SHALL be able to decline explicitly. Reporting the result of the town bid SHALL count as declining every roll still open, because players often start bidding without saying they skip the roll.

#### Scenario: Explicit decline
- **WHEN** both eligible players decline
- **THEN** the section ends, nobody pays, and the town bid starts with the original pair

#### Scenario: Skipped by bidding
- **WHEN** both players may still roll and someone reports the town bid result
- **THEN** the bot notes that the open rolls were skipped and accepts the result

#### Scenario: One rolls, one declines
- **WHEN** P1 rolls and P2 declines
- **THEN** the section ends and the town bid starts with the new pair

#### Scenario: Waiting on the other player
- **WHEN** P1 has rolled and P2 has neither rolled nor declined
- **THEN** the section stays open, and the bot's reminder names P2

### Requirement: Only allowed towns are accepted
Every town a player names (a banned town, the chosen town) SHALL be one of the towns allowed in the game's phase. When a player starts typing a town, the bot SHALL offer only allowed towns.

#### Scenario: Unknown town
- **WHEN** a player reports a town that is not in the catalogue
- **THEN** the bot refuses and lists the allowed towns

#### Scenario: Town not allowed in this phase
- **WHEN** the phase allows only Castle, Rampart and Tower and a player reports Cove
- **THEN** the bot refuses and lists the three allowed towns

### Requirement: Town bid is reported
In the town section the player named by the bot starts the bidding with others raising by at least 100, between the players, in the thread. After the bidding, either player SHALL report the winner, the amount and the chosen town. The town SHALL be one of the current pair. The winner pays the amount to the opponent.

#### Scenario: Winning bid
- **WHEN** P1 wins at 2100 and chooses Necropolis from Necropolis vs Tower
- **THEN** P1 pays 2100 to P2, P1 plays Necropolis and P2 plays Tower

#### Scenario: Town not in the pair
- **WHEN** the reported town is not in the pair
- **THEN** the bot refuses and repeats the pair

#### Scenario: More than the player has
- **WHEN** the amount is more than the payer's gold
- **THEN** the bot refuses

### Requirement: Color bid is reported
In the color section the players SHALL bid in the same way. Either player SHALL report the winner, the amount and the chosen color (red or blue). The winner pays the amount to the opponent. Red moves first.

#### Scenario: Winning bid
- **WHEN** P2 wins at 3000 and takes red
- **THEN** P2 pays 3000 to P1, P2 plays red and moves first

### Requirement: The bot keeps the gold
The bot SHALL keep each player's gold from the starting gold of the game's difficulty, with every payment going to the opponent. Gold moves in steps of 100: every payment (a bid, a roll cost) SHALL be a whole number of hundreds, 0 meaning nobody bid. A format SHALL NOT set a roll cost that is not a whole number of hundreds. The gold is stated in full when a trade starts (each player's starting gold) and is what the checks use. After that, because players think in differences, the thread SHALL show the gold as the difference from the starting gold, for both players, after each report and when a trade is reopened.

#### Scenario: Worked example
- **WHEN** the game is on 160% difficulty (10000 gold each), P1 pays a 500 roll, P1 pays 2100 for the town, and P2 pays 3000 for color
- **THEN** P1 ends with 10400 and P2 with 9600, shown as P1 +400 and P2 -400

#### Scenario: Not a whole hundred
- **WHEN** a player reports a bid of 2150
- **THEN** the bot refuses and says gold moves in steps of 100

#### Scenario: Difference shown after each section
- **WHEN** a section is reported
- **THEN** the thread shows how far each player is from the starting gold, for example "P1 -2100, P2 +2100"

#### Scenario: Starting gold shown at the start
- **WHEN** a trade starts
- **THEN** the thread shows each player's starting gold, for example 10000 each at 160% difficulty

### Requirement: Either player may report, and undo
Either player SHALL be able to report a section's result, with no confirmation from the other. Either player SHALL be able to undo the most recent player report (a bid result, a town or color choice) in the same game's trade. Random results drawn by the bot (a pair, a toss) and the rolls that caused them are final and SHALL NOT be undone.

#### Scenario: Opponent reports
- **WHEN** the loser of a bid reports the result
- **THEN** it is accepted and posted, naming who reported it

#### Scenario: Correcting a mistake
- **WHEN** a player undoes the last report
- **THEN** the gold and section return to how they were before it, and the bot asks for the result again

#### Scenario: Undoing a roll
- **WHEN** a player tries to undo a roll, or the report right after a roll
- **THEN** the bot refuses and says random results are final, so a roll cannot be redone for a better pair

#### Scenario: Nothing to undo
- **WHEN** a player asks to undo before any report in that game
- **THEN** the bot says there is nothing to undo

### Requirement: Final lobby settings
When the color section is done, the bot SHALL post the lobby settings for the game as one message: game number, template, each player's town, color and gold difference from the starting gold. At 200% difficulty the towns are not listed, because the game assigns them.

#### Scenario: Summary
- **WHEN** the last section of game 1 is reported
- **THEN** the thread shows template JC, P1 Necropolis with gold +400, and P2 Tower with gold -400, each with their color

### Requirement: At 200% difficulty only the color is tossed
A game on 200% difficulty is started with all-random towns and nobody has gold, so there is no town roll, no town choice and no bidding. The trade SHALL be one toss section: the bot tosses a fair coin between the players and announces the winner, and the winner chooses red or blue. No gold changes hands.

#### Scenario: Toss for color
- **WHEN** a 200% game starts its trade and P1 wins the toss and chooses red
- **THEN** P1 plays red and moves first, P2 plays blue, and no gold is paid

#### Scenario: Fair toss
- **WHEN** many 200% games are traded
- **THEN** each player has an equal chance of winning the toss

#### Scenario: No town steps
- **WHEN** a 200% game starts its trade
- **THEN** the bot does not ask for a roll, a town or a bid

#### Scenario: Summary
- **WHEN** the toss section is reported
- **THEN** the lobby settings show the template, the colors, who moves first, and that the game assigns the towns

### Requirement: Trade sections come from data
The list of sections of a trade SHALL come from data, so a template can later add or remove a section. Unless a template names its own, the sections SHALL follow from the difficulty: town roll, town bid and color bid below 200%, and the color toss alone at 200%.

#### Scenario: Default sections
- **WHEN** a template does not name sections and the game is on 160% difficulty
- **THEN** town roll, town bid and color bid are used

#### Scenario: Default sections at 200%
- **WHEN** a template does not name sections and the game is on 200% difficulty
- **THEN** only the color toss is used

Open question: who bids first in games after the first, including the decider. Provisional default: A bids first in every game. Players mostly agree among themselves, so this will be tuned once the interaction exists.

Open question: details of the roll. Provisional defaults: bans are chosen from the current pair; the new pair is drawn from all allowed towns that are not banned, so an unbanned town of the old pair may come back; bans stay in force for the rest of that game's roll section; the roll cost is paid gold, so it also reduces what a player can bid.

Open question: who chooses when nobody bids.