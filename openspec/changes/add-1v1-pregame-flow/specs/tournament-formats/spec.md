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
A format SHALL consist of one or more phases (for example group stage, early knockout, late knockout). Each phase SHALL define its best-of (1, 2, 3, 5, 7 or 9), the templates it uses (its pool), and how templates are chosen.

#### Scenario: Single-phase format
- **WHEN** a format has exactly one phase
- **THEN** players starting a match in that mode are never asked for a phase

#### Scenario: Multi-phase format
- **WHEN** a format has three phases with different pools, such as the 3-template group stage and the 7- and 9-template knockout stages
- **THEN** each phase is selectable on its own and uses only its own pool and best-of

### Requirement: A tournament lists its templates and each phase selects from them
A format SHALL list every template used in the tournament, each once. Each phase SHALL use some or all of them as its pool: a phase that states no pool uses all the listed templates, and a phase pool SHALL NOT contain a template that is not in the list.

#### Scenario: One phase, no pool
- **WHEN** a format lists JC, 6lm10a and h3dm1 and its only phase states no pool
- **THEN** the phase uses all three

#### Scenario: A phase uses some of the templates
- **WHEN** a format lists nine templates and its group stage names a pool of three of them
- **THEN** the group stage uses those three, and a knockout phase that states no pool uses all nine

#### Scenario: Template not in the list
- **WHEN** a phase pool contains a template that the format does not list
- **THEN** validation fails and names the template and the templates that are listed

#### Scenario: Template listed twice
- **WHEN** a template is listed twice, or twice in one pool
- **THEN** validation fails and names it

### Requirement: Template choice is either a sequence or agreed
A phase SHALL choose templates either by an ordered sequence of steps, or by agreement, where the players name the template themselves. A step is a ban or a pick by a named player (A or B), or the decider: the template that is left, which no player chooses. A is the coinflip winner and B is the other player.

#### Scenario: Sequence format
- **WHEN** a phase has the sequence A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban, decider
- **THEN** the bot runs exactly those steps in that order, and the decider takes the one template that is left

#### Scenario: Agreed format
- **WHEN** a phase is marked as agreed, as in ranked mode
- **THEN** no bans or picks happen and the players supply the template when starting the match

### Requirement: Format files are validated
A format file SHALL be rejected, with a message naming the problem, unless: for a sequence phase the pool holds exactly as many templates as the sequence has steps, because each template is banned, picked or the decider; the decider, if there is one, is the last step and names no player; the picks plus the decider, if there is one, make as many games as the best-of; every template is known; and the file has all required fields.

#### Scenario: Pool does not fit the sequence
- **WHEN** a phase has a pool of 9 templates and a sequence of 7 steps
- **THEN** validation fails and says the pool must have as many templates as the sequence has steps

#### Scenario: Valid BO1 group stage
- **WHEN** a phase has best-of 1, a pool of 3 templates and the sequence A ban, B ban, decider
- **THEN** validation passes and the decider takes the remaining template, which is the only game

#### Scenario: Wrong number of games
- **WHEN** a phase has best-of 3 and the sequence A ban, B ban, decider
- **THEN** validation fails and says a best-of-3 needs 3 games and the sequence gives 1

#### Scenario: Decider in the wrong place
- **WHEN** the decider is not the last step, or it names a player
- **THEN** validation fails and says where the decider must be

### Requirement: The games follow from the sequence
The games of a sequence phase SHALL be played in the order of its picks as they appear in the sequence, followed by the decider if the sequence has one. A format SHALL NOT state the order of the games separately.

#### Scenario: Picks, then the decider
- **WHEN** a phase has the sequence A ban, B ban, A pick, B pick, decider
- **THEN** game 1 uses A's picked template, game 2 B's, and game 3 the template the decider took

#### Scenario: Both games picked, no decider
- **WHEN** a best-of-2 phase has the sequence A ban, B ban, A pick, B pick and no decider
- **THEN** the two games are A's pick and B's pick, in that order

### Requirement: Roll rules can be set for the tournament, a template, or a template in one phase
Roll rules (the cost of a town roll, the number of rolls each player has, and the maximum number of towns banned per roll) SHALL be settable for the whole tournament, for a template in the format's list of templates, and for a template in one phase's pool. The most specific setting wins, field by field: the built-in defaults of 500 gold, 1 roll per player and banning 0 to 2 towns, then the tournament's rules, then the template's, then the phase's entry for the template.

#### Scenario: Tournament rules
- **WHEN** the tournament sets the roll cost to 300 and nothing more specific is written
- **THEN** every roll costs 300

#### Scenario: Rules of one template
- **WHEN** the tournament sets the roll cost to 500 and a template in the list sets it to 0
- **THEN** rolls on that template are free in every phase and rolls on the others cost 500

#### Scenario: Rules of a template in one phase
- **WHEN** a template's entry in one phase's pool sets rolls per player to 2
- **THEN** in that phase the template allows two rolls each, and in the other phases it keeps its other rules

#### Scenario: Field by field
- **WHEN** a template sets the roll cost to 0 and its entry in a phase sets only the rolls per player to 2
- **THEN** both apply to that template in that phase

#### Scenario: Roll defaults
- **WHEN** nothing sets any roll rule
- **THEN** the defaults are one roll per player at 500 gold, banning 0 to 2 towns

### Requirement: Starting gold follows from the template's difficulty
Each template in the catalogue SHALL state its difficulty. A format SHALL NOT state a difficulty or starting gold. Each player's starting gold SHALL be what the game gives a human player at the template's difficulty: 80% gives 30000, 100% gives 20000, 130% gives 15000, 160% gives 10000 and 200% gives 0. A template with any other difficulty SHALL be rejected.

#### Scenario: 130% difficulty
- **WHEN** a game is played on a template with 130% difficulty
- **THEN** both players start the trade with 15000 gold

#### Scenario: 160% difficulty
- **WHEN** a game is played on a template with 160% difficulty
- **THEN** both players start the trade with 10000 gold

#### Scenario: 200% difficulty
- **WHEN** a game is played on a template with 200% difficulty
- **THEN** both players start with 0 gold, and the trade is only a toss for color (the trade of such a game is a follow-up change)

#### Scenario: Difficulty or gold written in a format file
- **WHEN** a format file contains a difficulty or a starting gold value
- **THEN** validation fails and names the unexpected field

#### Scenario: Template without a difficulty
- **WHEN** a template in the catalogue has no difficulty, or one that is not supported
- **THEN** the catalogue is refused and the message names the template

### Requirement: Templates come from one catalogue
The bot SHALL take the list of templates from a single JSON catalogue in the repository, shared by all formats. Every template in the format's list of templates SHALL be in the catalogue. A contributor adds a template by editing the catalogue only. The catalogue gives each template an id, the name players use, and its difficulty.

#### Scenario: Known templates
- **WHEN** a format lists JC, 6lm10a and h3dm1, and all three are in the catalogue
- **THEN** the format passes validation on that point

#### Scenario: Unknown template
- **WHEN** a format lists a template that is not in the catalogue
- **THEN** validation fails and names the unknown template

#### Scenario: New template
- **WHEN** a template is added to the catalogue
- **THEN** it can be listed in any format

### Requirement: The repository ships a working format
The repository SHALL contain at least one valid, active format, so that a fresh checkout can start a match without anyone adding a format first. Which formats ship is not part of this requirement: a format made for development can be replaced by real tournaments without changing anything else.

#### Scenario: Fresh checkout
- **WHEN** the bot is started from a fresh checkout
- **THEN** at least one mode is listed and a match can be started in it

#### Scenario: Replacing the development format
- **WHEN** real formats are added and the development format is removed
- **THEN** the bot, its specs and its tests need no other change

### Requirement: Towns come from one catalogue
The bot SHALL take the list of towns from a single JSON catalogue in the repository, shared by all formats. A format MAY restrict the towns allowed for the whole tournament to a subset of the catalogue, and a phase MAY give its own list, which replaces the tournament's for that phase. If neither does, all towns in the catalogue are allowed. A contributor adds a town by editing the catalogue only.

#### Scenario: Default
- **WHEN** neither the tournament nor a phase names allowed towns
- **THEN** every town in the catalogue is allowed in its games

#### Scenario: Restricted tournament
- **WHEN** a tournament allows only Castle, Rampart and Tower and a phase names no towns
- **THEN** reports in that phase's games accept only those three towns

#### Scenario: A phase has its own list
- **WHEN** a tournament allows only Castle and Rampart and its final names Tower, Castle and Cove
- **THEN** the final allows exactly those three towns, and the other phases still allow only Castle and Rampart

#### Scenario: Unknown town in a format
- **WHEN** the tournament or a phase restricts the towns to a name that is not in the catalogue
- **THEN** validation fails and names the unknown town

#### Scenario: New town
- **WHEN** a town is added to the catalogue
- **THEN** it is allowed everywhere that does not restrict its towns, with no other change

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

Open question: whether any tournament plays its games in an order other than the order of the picks. If one does, a pick will get an optional game number. Until then the bot assumes the order of the picks.

Open question: at 200% (Impossible) the wiki mentions 2500 gold and some extra resources when tournament rules are enabled. Until confirmed, 200% gives 0 gold.
