## ADDED Requirements

### Requirement: A game's trade has a kind
The kind of a game's trade SHALL be the `trade` setting of the game's template in the match's phase. The kinds are the standard trade (the one this capability describes everywhere else), the trade with computer-player packs, and the roulette. When nothing is stated, the kind is the standard one. A mirror template keeps its kind, changed as the requirement about a mirror trade says. When a trade of any other kind opens, the thread SHALL say which kind it is.

#### Scenario: Nothing stated
- **WHEN** a game's template states no trade
- **THEN** the trade is the standard one, and the thread says nothing about a kind

#### Scenario: The kind depends on the phase
- **WHEN** a tournament trades Nostalgia as a standard trade in the groups and as a roulette in the final
- **THEN** a game of Nostalgia in the groups has a standard trade and one in the final has a roulette trade

#### Scenario: Saying the kind
- **WHEN** the trade of a game on a template with computer-player packs opens
- **THEN** the thread's opening message says the trade has computer-player packs

### Requirement: A mirror trade draws one town and bids only on the color
When the template of a game is a mirror and its trade is the standard one, the bot SHALL draw one town, which both players play, instead of a pair. A roll SHALL pay the roll cost to the opponent, ban the town that stands (a roll names no towns) and draw another town from the allowed towns that are not banned. The only bid SHALL be the color bid, in which the winner takes the color. How the starting heroes are banned and chosen is not run by the bot.

#### Scenario: Announcement
- **WHEN** the trade of a mirror game starts
- **THEN** the thread says that both players play one town, for example "Necropolis", the roll cost and who may roll

#### Scenario: A roll
- **WHEN** the town is Necropolis and P1 rolls
- **THEN** P1 pays the roll cost to P2, Necropolis is banned for the rest of the roll section, and the bot announces a new town that is not Necropolis

#### Scenario: No town bid
- **WHEN** the roll section of a mirror trade is over
- **THEN** the color bid is expected next, and reporting a town is refused with a message that says so

#### Scenario: No town left
- **WHEN** a roll would leave no allowed town to draw
- **THEN** the bot refuses the roll and nobody pays

#### Scenario: The color bid
- **WHEN** P2 wins the color bid at 3000 and takes red
- **THEN** P2 pays 3000 to P1, plays red and moves first, and both play the drawn town

### Requirement: A trade with computer-player packs draws the pair and two packs
For a trade with computer-player packs the bot SHALL draw a pair of towns and two packs of three towns each for the computer players, named pack1 and pack2, all eight towns different and allowed in the phase, and announce them. A roll SHALL name towns of the player pair to ban, as in a standard roll, and the bot SHALL redraw the pair and both packs. A banned town is banned for the players only: it SHALL NOT be in the new pair, but it MAY come up in a pack. After the town bid comes the pack bid and then the color bid.

#### Scenario: Announcement
- **WHEN** the trade of a game on such a template starts
- **THEN** the thread says the pair, pack1 and pack2 with their three towns each, the roll cost and who may roll

#### Scenario: A roll redraws everything
- **WHEN** a player rolls banning Castle from the pair
- **THEN** the roller pays, and the bot announces a new pair without Castle and two new packs, all eight towns different

#### Scenario: A banned town in a pack
- **WHEN** a player has banned Castle
- **THEN** Castle can come up in a pack of the new draw, but never in the pair

#### Scenario: Only the player pair can be banned
- **WHEN** a player rolls naming a town that is in a pack
- **THEN** the bot refuses, says only the towns of the pair can be banned, and nobody pays

#### Scenario: Exactly eight allowed towns
- **WHEN** the phase allows exactly eight towns and a player rolls banning one of the pair
- **THEN** the roll works: the new pair is two of the other towns, and the banned town is in a pack

#### Scenario: Fewer than two towns left for the pair
- **WHEN** the bans would leave fewer than two allowed towns that are not banned
- **THEN** the bot refuses the roll and nobody pays

#### Scenario: The pack bid
- **WHEN** P1 wins the pack bid at 1200 and chooses pack2
- **THEN** P1 pays 1200 to P2, P1 gets pack2 and P2 gets pack1

#### Scenario: A pack that does not exist
- **WHEN** a player reports the pack bid choosing pack3
- **THEN** the bot refuses and says the choice is pack1 or pack2

### Requirement: After a game's trade the thread says what is next
When the last section of a game's trade is done, the bot SHALL post the lobby settings and then say what comes next in the match: the next ban or pick, when the selection is not done, and the next game whose trade is not finished, when there is one that is decided, with how to start its trade. When every game of the match is traded, it SHALL say so.

#### Scenario: The selection is not done
- **WHEN** the trade of game 1 of a best-of-3 is done while the bans and picks are still going
- **THEN** the thread gives the lobby settings and then the next step, for example "Step 3 of 4: <@1> picks a template with /pick"

#### Scenario: Another game is decided
- **WHEN** the trade of game 1 is done and game 2 is decided but not traded
- **THEN** the thread gives the lobby settings and then says game 2 can be traded with /trade start

#### Scenario: The next step and a game to trade
- **WHEN** the trade of game 1 is done, game 2 is decided and a pick is still to be made
- **THEN** the next step comes first and the way to start the trade of game 2 comes last

#### Scenario: Every game is traded
- **WHEN** the trade of the last game of the match is done
- **THEN** the thread gives the lobby settings and says every game of the match is traded

#### Scenario: A match of one game
- **WHEN** the trade of a match that started with a named template is done
- **THEN** the thread says that was the only game, as before

### Requirement: The pack bid can be undone
The pack bid SHALL be undone by the undo of the `match-setup` capability like any other step.

#### Scenario: Undoing a pack bid
- **WHEN** both players agree to undo from the pack bid
- **THEN** the pack bid stops counting and the bot asks for it again, with the same pair and packs

## MODIFIED Requirements

### Requirement: The trade runs in sections
The trade of a game SHALL run in sections, in an order that its kind fixes. The standard trade runs town roll, town bid, color bid. Each section starts with a bot message that says what to do, who starts and the minimum raise (100 gold). The bot SHALL not accept a result for a section until the sections before it are done.

#### Scenario: Prompting
- **WHEN** a trade starts
- **THEN** the bot posts the template, each player's starting gold, and the first section's instruction (for the roll section, the generated pair, the roll cost and who may roll)

#### Scenario: Out of order
- **WHEN** a player reports a color bid before the town bid is done
- **THEN** the bot refuses and names the section that is expected

### Requirement: The bot generates the town pair
When the roll section of a standard trade starts, the bot SHALL draw two different towns at random, each allowed town equally likely, and announce in the thread the pair, the roll cost, and which players may roll (the first player, the second player, or both). A player may roll only if they have a roll left and enough gold for the cost. Players set the announced towns in the lobby by hand. The other kinds draw as their own requirements say.

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
An eligible player SHALL be able to roll by naming the towns to ban (0 up to the allowed maximum), from the current pair. The roller SHALL pay the roll cost to the opponent. The bot SHALL then draw a new pair of two different towns from the allowed towns that are not banned, and announce the new pair, the roll cost, and who may still roll. The other kinds roll as their own requirements say.

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

### Requirement: Final lobby settings
When the last section of a trade is done, the bot SHALL post the lobby settings for the game as one message: game number, template, the settings typed into the lobby as far as they are stated (timer, map size, roads, computer players), and what the kind decided, with each player's gold difference from the starting gold. For a standard trade that is each player's town and color; for a mirror, the one town and each player's color; for packs, also each player's pack; for a roulette, each player's town and hero, or the drawn heroes and who chooses what.

#### Scenario: Summary
- **WHEN** the last section of game 1 is reported
- **THEN** the thread shows template JC, P1 Necropolis with gold +400, and P2 Tower with gold -400, each with their color

#### Scenario: Summary with the lobby settings
- **WHEN** the last section of a game is reported, and its timer is `12:00+06:00+02:00`, its map size `L+U`, its roads `mid` and it has 3 computer players
- **THEN** the lobby settings include "Timer: 12:00+06:00+02:00", "Map: L+U", "Roads: mid" and "AI players: 3" with the other settings

#### Scenario: Summary without them
- **WHEN** nothing is stated for the game's template and the tournament sets no timer
- **THEN** the lobby settings have none of these lines

#### Scenario: A mirror
- **WHEN** the color bid of a mirror game is reported
- **THEN** the lobby settings give the town both players play, and each player's color and gold

#### Scenario: Packs
- **WHEN** the color bid of a game with packs is reported
- **THEN** the lobby settings give each player's town, the towns of the pack of each player, color and gold

#### Scenario: A mirror roulette
- **WHEN** the bid of a mirror roulette is reported
- **THEN** the lobby settings give the town, the two drawn heroes, who chooses what, and each player's gold, and no colors

### Requirement: Each eligible player rolls or skips the roll
The roll section SHALL end when no eligible player is left who has neither rolled nor skipped since the towns last changed. A player SHALL be able to skip explicitly, which passes on the towns that stand and leaves the trade itself open. A skip lasts only until the towns change: when the other player rolls, the one who skipped SHALL be able to roll again, if they still have a roll and enough gold, or to skip again. Reporting the result of the first bid SHALL count as skipping every roll still open, and the bot SHALL record that skip for each player whose roll was open, before the bid, so that undoing the bid alone does not open the roll section again, because players often start bidding without saying they skip the roll.

#### Scenario: Explicit skip
- **WHEN** both eligible players skip the roll
- **THEN** the section ends, nobody pays, and the bid starts with the original towns

#### Scenario: Skipped by bidding
- **WHEN** both players may still roll and someone reports the first bid
- **THEN** the bot records a skip for each open roll and accepts the result

#### Scenario: Undoing the bid keeps the rolls skipped
- **WHEN** a bid skipped the open rolls and then only that bid is undone
- **THEN** the bid is expected again and the roll section stays closed; it opens again only if the recorded skip itself is undone

#### Scenario: One rolls, one skips
- **WHEN** P1 rolls their only roll and P2 skips the roll
- **THEN** the section ends and the bid starts with the new towns

#### Scenario: A skip does not use up the roll
- **WHEN** P1 skips and then P2 rolls, which draws new towns
- **THEN** P1 may roll again, to ban the new towns, or skip again, and the section stays open until each of them has rolled or skipped since the towns last changed

#### Scenario: Both skip the new towns
- **WHEN** P1 skips, P2 rolls, and then P1 and P2 both skip
- **THEN** the section ends and the bid starts with the towns that stand

#### Scenario: Skipping twice
- **WHEN** a player who has skipped tries to skip or roll before the towns change
- **THEN** the bot refuses and says they have already passed on these towns

#### Scenario: Waiting on the other player
- **WHEN** P1 has skipped and P2 has neither rolled nor skipped
- **THEN** the section stays open, and the bot's reminder names P2

### Requirement: Trade sections come from data
The sections of a trade SHALL come from its kind, which is data (the `trade` setting of the template in the tournament's format), so a template can be traded in another way in another phase without a change to the bot. Unless a kind is stated, the sections SHALL be town roll, town bid and color bid. (Games on 200% difficulty, whose trade is only a toss for color, are a follow-up change; until then the bot says their trade is not available.)

#### Scenario: Default sections
- **WHEN** no trade kind is stated and the game is on 160% difficulty
- **THEN** town roll, town bid and color bid are used

#### Scenario: Sections of a kind
- **WHEN** the kind of a game is the mirror trade
- **THEN** the sections are town roll and color bid

#### Scenario: A 200% game
- **WHEN** a player starts the trade of a game on 200% difficulty
- **THEN** the bot says the trade of such a game is not available yet and posts nothing

Open question: who bids first in games after the first, including the decider. Provisional default: A bids first in every game. Players mostly agree among themselves, so this will be tuned once the interaction exists.

Open question: details of the roll. Provisional defaults: bans are chosen from the current pair; the new pair is drawn from all allowed towns that are not banned, so an unbanned town of the old pair may come back; bans stay in force for the rest of that game's roll section; the roll cost is paid gold, so it also reduces what a player can bid.

Open question: who chooses when nobody bids.
