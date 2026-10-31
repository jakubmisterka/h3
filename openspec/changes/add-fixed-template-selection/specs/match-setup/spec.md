## ADDED Requirements

### Requirement: A match in a fixed phase plays every game on the phase's template
In a fixed phase the starting player SHALL NOT need to name a template. The bot SHALL take the phase's only template, post the rules of the match (the format as BO and the number of games, and what is stated about the template, as for a match with a named template), do the coinflip and open the trade of game 1 itself. The match SHALL have as many games as the best-of of the phase, all on that template. When the trade of a game is done, the bot SHALL say which game is next and how to start its trade, until every game has been traded, and then say that every game is traded. A player who names the phase's template SHALL get the same match. A player who names another template SHALL be refused, with the template of the phase listed. The ban and pick commands SHALL say that this phase has no bans or picks.

#### Scenario: Start without a template
- **WHEN** a player starts a match in a fixed best-of-3 phase and names no template
- **THEN** the thread says "Format: BO3" and what is stated about the template, the coinflip is done and the trade of game 1 is opened

#### Scenario: The next game
- **WHEN** the trade of game 1 of a fixed best-of-3 phase is done
- **THEN** after the lobby settings the bot says "Game 2 is Nostalgia. Start its trade with /trade start."

#### Scenario: Every game traded
- **WHEN** the trades of all three games of a fixed best-of-3 phase are done
- **THEN** the bot says every game of the match has been traded

#### Scenario: Another template named
- **WHEN** a player starts a match in a fixed phase and names a template that is not the phase's
- **THEN** the bot refuses, creates no thread and lists the template the phase uses

#### Scenario: Bans in a fixed phase
- **WHEN** a player uses the ban or pick command in a match of a fixed phase
- **THEN** the bot says this phase has no bans or picks

#### Scenario: The overview
- **WHEN** a player asks for the status of a match in a fixed best-of-3 phase
- **THEN** the overview shows three games, each on the phase's template, and no template selection
