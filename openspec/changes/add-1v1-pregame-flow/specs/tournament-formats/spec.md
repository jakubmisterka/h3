# Spec Delta

## Purpose

Defines the tournament formats players can choose from: the rules of the pre-game phase for one tournament or ranked mode, kept as JSON files in the repository so contributors can add formats by pull request.

## ADDED Requirements

### Requirement: Formats are files in the repository
Every format SHALL be one JSON file in the repository. All servers SHALL choose from the same catalogue, and a format SHALL behave the same on every server.

#### Scenario: Contributor adds a format
- **WHEN** a contributor adds a valid format file and the change is merged
- **THEN** the format appears in the list of modes players can start a match with, with no code change

#### Scenario: Same format on two servers
- **WHEN** two servers start a match in the same mode
- **THEN** both matches follow identical rules

### Requirement: A format has one or more phases
A format SHALL consist of one or more phases (for example group stage, early knockout, late knockout). Each phase SHALL define its best-of (1, 3 or 5), its template pool, and how templates are chosen.

#### Scenario: Single-phase format
- **WHEN** a format has exactly one phase
- **THEN** players starting a match in that mode are never asked for a phase

#### Scenario: Multi-phase format
- **WHEN** a format has three phases with different pools, such as the 3-template group stage and the 7- and 9-template knockout stages
- **THEN** each phase is selectable on its own and uses only its own pool and best-of

### Requirement: Template choice is either a sequence or agreed
A phase SHALL choose templates either by an ordered sequence of steps, each naming the acting player (A or B) and the action (ban or pick), or by agreement, where the players name the template themselves. A is the coinflip winner and B is the other player.

#### Scenario: Sequence format
- **WHEN** a phase has the sequence A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban
- **THEN** the bot runs exactly those steps in that order

#### Scenario: Agreed format
- **WHEN** a phase is marked as agreed, as in ranked mode
- **THEN** no bans or picks happen and the players supply the template when starting the match

### Requirement: Format files are validated
A format file SHALL be rejected, with a message naming the problem, unless: for a sequence phase the pool holds exactly one more template than the sequence has steps; the number of picks is one fewer than the best-of; the game order names every game of the best-of exactly once; every template is known; and the file has all required fields.

#### Scenario: Pool does not fit the sequence
- **WHEN** a phase has a pool of 9 templates and a sequence of 7 steps
- **THEN** validation fails and says the pool must be one larger than the number of steps

#### Scenario: Valid BO1 group stage
- **WHEN** a phase has best-of 1, a pool of 3 templates and the sequence A ban, B ban
- **THEN** validation passes and the remaining template is the only game

### Requirement: Game order is explicit
A phase SHALL state the order in which games are played, as a list over the picks and the decider (for example A's pick, B's pick, decider). The order SHALL NOT be assumed by the bot.

#### Scenario: Order from the file
- **WHEN** a phase states the order A's pick, B's pick, decider
- **THEN** game 1 uses A's picked template, game 2 B's, and game 3 the leftover template

### Requirement: Trade settings have tournament defaults and template overrides
A phase SHALL be able to set trade defaults: the game difficulty, the cost of a faction roll, the number of rolls each player has and the maximum number of factions banned per roll. Each template in the pool SHALL be able to override any of these.

#### Scenario: Template overrides a default
- **WHEN** a phase sets difficulty 160% and one template sets difficulty 130%
- **THEN** games on that template use the 130% difficulty and the others use 160%

#### Scenario: No override
- **WHEN** a template sets nothing
- **THEN** the phase defaults apply

### Requirement: Starting gold follows from the difficulty
A format SHALL NOT state starting gold. Each player's starting gold SHALL be the amount the game gives a human player at the game's difficulty: 80% gives 30000, 100% gives 20000, 130% gives 15000, 160% gives 10000 and 200% gives 0. A format that names any other difficulty SHALL be rejected.

#### Scenario: 130% difficulty
- **WHEN** a game is played on 130% difficulty
- **THEN** both players start the trade with 15000 gold

#### Scenario: 160% difficulty
- **WHEN** a game is played on 160% difficulty
- **THEN** both players start the trade with 10000 gold

#### Scenario: 200% difficulty
- **WHEN** a game is played on 200% difficulty
- **THEN** both players start with 0 gold, and the trade is only a toss for color (see the `game-trade` spec)

#### Scenario: Starting gold written in the file
- **WHEN** a format file contains a starting gold value
- **THEN** validation fails and says the gold comes from the difficulty

#### Scenario: Roll defaults
- **WHEN** a phase sets no roll values and a template sets none
- **THEN** the defaults are one roll per player at 500 gold, banning 0 to 2 factions

### Requirement: Templates come from one catalogue
The bot SHALL take the list of templates from a single JSON catalogue in the repository, shared by all formats. Every template in a phase's pool, and every template named for an agreed-template phase, SHALL be in the catalogue. A contributor adds a template by editing the catalogue only. The catalogue gives each template an id and the name players use.

#### Scenario: Known templates
- **WHEN** a phase's pool is JC, 6lm10a and h3dm1, and all three are in the catalogue
- **THEN** the format passes validation on that point

#### Scenario: Unknown template in a pool
- **WHEN** a phase's pool contains a template that is not in the catalogue
- **THEN** validation fails and names the unknown template

#### Scenario: New template
- **WHEN** a template is added to the catalogue
- **THEN** it can be used in the pool of any format

### Requirement: El Classico is the first format
The first format SHALL be El Classico: one phase, best-of 1, a pool of JC, 6lm10a and h3dm1, all played on 160% difficulty, with the sequence A ban, B ban, so that the remaining template is the only game. Standard roll rules apply and all factions in the catalogue are allowed.

#### Scenario: Selection in El Classico
- **WHEN** A bans JC and B bans h3dm1
- **THEN** 6lm10a is the only game, and the trade starts with 10000 gold for each player

#### Scenario: Listed as a mode
- **WHEN** a player lists the modes
- **THEN** El Classico is shown

### Requirement: Factions come from one catalogue
The bot SHALL take the list of factions (towns) from a single JSON catalogue in the repository, shared by all formats. A phase MAY restrict the factions allowed in its games to a subset of the catalogue; if it does not, all factions in the catalogue are allowed. A contributor adds a faction by editing the catalogue only.

#### Scenario: Default
- **WHEN** a phase names no allowed factions
- **THEN** every faction in the catalogue is allowed in its games

#### Scenario: Restricted phase
- **WHEN** a phase allows only Castle, Rampart and Tower
- **THEN** reports in its games accept only those three factions

#### Scenario: Unknown faction in a format
- **WHEN** a phase restricts the factions to a name that is not in the catalogue
- **THEN** validation fails and names the unknown faction

#### Scenario: New faction
- **WHEN** a faction is added to the catalogue
- **THEN** it is allowed in all phases that do not restrict their factions, with no other change

### Requirement: Format controls thread visibility
A format SHALL state whether its match threads are public or private. If it states nothing, threads are public.

#### Scenario: Default visibility
- **WHEN** a format sets no visibility
- **THEN** its match thread can be read by everyone who can see the channel

### Requirement: Archived formats stay on record
A format that is no longer used SHALL be marked archived instead of deleted. Archived formats SHALL NOT be offered for new matches, and their file SHALL stay in the repository.

#### Scenario: Starting a match in an archived format
- **WHEN** a player tries to start a match in an archived mode
- **THEN** the bot refuses and says the mode is archived

#### Scenario: Archived formats in the list
- **WHEN** a player lists the modes
- **THEN** archived modes are not shown

### Requirement: Open rule questions are recorded
Where a tournament rule is unclear, the format and its spec SHALL record the question instead of guessing.

#### Scenario: Open question
- **WHEN** a rule is unclear
- **THEN** it is written as "Open question:" and the bot uses the stated provisional default

Open question: at 200% (Impossible) the wiki mentions 2500 gold and some extra resources when tournament rules are enabled. Until confirmed, 200% gives 0 gold.
