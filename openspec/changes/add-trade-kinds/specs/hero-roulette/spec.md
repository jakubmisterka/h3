## ADDED Requirements

### Requirement: Heroes come from one catalogue
The repository SHALL have a catalogue of heroes in `data/heroes.json`. Each hero SHALL have an id, a name, the id of its town (a town of the town catalogue) and a link, starting with `https://`, to the page that describes it on the community wiki. Ids SHALL be unique, ignoring letter case. A file that breaks this SHALL stop the bot from starting with a message that names the file and the hero.

#### Scenario: A valid hero
- **WHEN** the catalogue has a hero with id, name, a known town and a link
- **THEN** the catalogue is accepted

#### Scenario: Unknown town
- **WHEN** a hero names a town that is not in the town catalogue
- **THEN** the bot does not start, and the message names the hero and the unknown town

#### Scenario: A repeated id
- **WHEN** two heroes have the same id
- **THEN** the bot does not start, and the message names both entries

### Requirement: A template can list the heroes its map does not offer
A template in the catalogue MAY list `banned_heroes`, the ids of heroes of the hero catalogue that the template's map does not offer. Such a hero SHALL NOT be drawn in a roulette. An id that is not a hero of the catalogue, or one listed twice, SHALL stop the bot from starting with a message that names the template and the id.

#### Scenario: A list
- **WHEN** a template lists two heroes as banned
- **THEN** the catalogue is accepted, and those heroes are never drawn for that template

#### Scenario: Unknown hero
- **WHEN** a template lists a hero that is not in the hero catalogue
- **THEN** the bot does not start, and the message names the template and the hero

### Requirement: A roulette trade draws heroes after the rolls
When the trade of a game is a roulette, the bot SHALL draw the town or towns and let them be rolled as in the trade this template would otherwise have. When the roll section is over, each player in turn (the coinflip winner first) SHALL be able to ban up to the tournament's number of heroes of the drawn town or towns (the number may be 0, and then there is no ban step). Then the bot SHALL draw the heroes and announce them: for a mirror two different heroes of the town, otherwise one hero of each town of the pair. A banned hero, and a hero the template does not offer, SHALL NOT be drawn. The draw SHALL be final.

#### Scenario: Bans, then the draw
- **WHEN** the roll section of a roulette with one hero ban each is over
- **THEN** the coinflip winner may ban up to one hero, then the other player may, and then the bot draws and announces the heroes

#### Scenario: No bans
- **WHEN** the roll section of a roulette without hero bans is over
- **THEN** the bot draws and announces the heroes at once

#### Scenario: A mirror roulette
- **WHEN** the drawn town is Necropolis in a mirror roulette
- **THEN** the bot announces two different heroes of Necropolis

#### Scenario: A roulette with a pair
- **WHEN** the pair is Castle vs Tower in a roulette that is not a mirror
- **THEN** the bot announces one hero of Castle and one hero of Tower, and the thread shows each town with its hero

#### Scenario: Hero the template does not offer
- **WHEN** a template lists a hero of the drawn town as banned
- **THEN** that hero is never drawn

#### Scenario: Banning a hero that cannot be banned
- **WHEN** a player bans a hero that is not of the drawn town or towns, or more heroes than the tournament allows, or out of turn
- **THEN** the bot refuses and says why

#### Scenario: Too few heroes
- **WHEN** a ban would leave too few heroes to draw
- **THEN** the bot refuses it

#### Scenario: Bidding too early
- **WHEN** a player reports a bid before the heroes are drawn
- **THEN** the bot refuses and says what comes first

#### Scenario: The draw is final
- **WHEN** the heroes are drawn
- **THEN** there is no way to draw them again except undoing from the last step before the draw, which needs both players

### Requirement: A tournament can have the roulette heroes drawn with the towns
When the roulette setting `roll_before_heroes` is false, the bot SHALL draw the heroes together with the town or towns when the trade starts and announce them with the towns. A roll SHALL redraw the towns and the heroes together. There SHALL be no hero bans.

#### Scenario: Announcement
- **WHEN** the trade of a roulette with `roll_before_heroes` false starts
- **THEN** the thread announces the town or towns and the heroes together, and says who may roll

#### Scenario: A roll
- **WHEN** a player rolls in such a trade
- **THEN** the roller pays, and the bot announces new towns and new heroes of the new towns

### Requirement: A roulette that is not a mirror bids on the town and on the color
In a roulette that is not a mirror, the town bid SHALL be reported by naming the town; the player who plays that town also plays the hero drawn for it, and the other player plays the other town and its hero. The color bid follows as in the standard trade.

#### Scenario: Town bid in a roulette
- **WHEN** P1 wins the town bid at 1500 and names Tower, whose hero is Hero X
- **THEN** P1 pays 1500 to P2, P1 plays Tower with Hero X, and P2 plays the other town with its hero

### Requirement: A mirror roulette has one bid on who chooses first
In a mirror roulette there SHALL be one bid. Its winner reports the amount and whether they choose first the hero or the color. The winner pays the amount to the opponent. The thread SHALL say who chooses what: the winner chooses the one named, and the other player chooses the other. The bot SHALL NOT ask which hero or which color is chosen.

#### Scenario: The winner takes the hero first
- **WHEN** P1 wins at 800 and reports that they choose the hero first
- **THEN** P1 pays 800 to P2, and the thread says P1 chooses the hero first from the two drawn heroes and P2 chooses the color

#### Scenario: The winner takes the color first
- **WHEN** P2 wins at 0 and reports that they choose the color first
- **THEN** nobody pays, and the thread says P2 chooses the color and P1 chooses the hero first

#### Scenario: A choice that is not hero or color
- **WHEN** a player reports the bid naming something else
- **THEN** the bot refuses and says the choice is hero or color

### Requirement: The steps of a roulette can be undone
Hero bans and the bid of a roulette SHALL be undone by the undo of the `match-setup` capability like any other step. The draw of the heroes is made by the bot together with the step that completes the roll section or the bans, so undo SHALL NOT start at the draw alone: it starts at the step before it, and the heroes are drawn again after it.

#### Scenario: Undoing a hero ban
- **WHEN** both players agree to undo from a hero ban made before the draw
- **THEN** the ban and the draw stop counting, and the bot asks for the ban again

#### Scenario: Undoing the bid
- **WHEN** both players agree to undo from the bid of a roulette
- **THEN** the bid stops counting and the bot asks for it again, with the same heroes

#### Scenario: Undoing from the draw alone
- **WHEN** a player asks to undo from the record of the hero draw
- **THEN** the bot refuses and says to undo from the step before it
