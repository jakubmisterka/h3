# Spec Delta

## Purpose

Lets players look up how a tournament mode works and how a template is played in it, without starting a match. It also gives contributors a quick way to check that a new format file says what they meant.

## ADDED Requirements

### Requirement: A player can look up a mode
A player SHALL be able to ask for the information about a mode by naming it. The reply SHALL give the mode's name and, for each phase, its name, its best-of and the templates in its pool. The mode SHALL be found by its id or its name, ignoring case.

#### Scenario: Single-phase mode
- **WHEN** a player asks about El Classico
- **THEN** the reply names El Classico, one phase with best of 1, and the templates JC, 6lm10a and h3dm1

#### Scenario: Multi-phase mode
- **WHEN** a player asks about a mode with three phases
- **THEN** the reply lists every phase with its own best-of and its own pool

### Requirement: Mode info says how templates are chosen
For each phase, the reply SHALL say in plain words how the template is chosen: the order of bans and picks with who acts (A is the coinflip winner, B the other player), and in which order the games are played. For a phase where players agree on the template, it SHALL say so.

#### Scenario: Ban, ban
- **WHEN** a player asks about El Classico
- **THEN** the reply says that A bans, then B bans, and the last template is played

#### Scenario: Bans and picks
- **WHEN** a phase has the sequence A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban
- **THEN** the reply lists those steps in that order and says the games are played as the format states, ending with the leftover template

#### Scenario: Agreed template
- **WHEN** a player asks about a mode where players agree on the template
- **THEN** the reply says the players agree on the template, and lists the templates allowed

### Requirement: A player can look up a template in a mode
A player SHALL be able to ask about one template in a mode. The reply SHALL say, for each phase of the mode that has the template in its pool, the difficulty, the starting gold that follows from it, and the roll rules that apply to that template: the cost of a roll, the rolls each player has, and the most factions banned per roll. Overrides for that template SHALL be applied.

#### Scenario: Template with the defaults
- **WHEN** a player asks about JC in El Classico
- **THEN** the reply says phase Main, 160% difficulty, 10000 gold each, a roll costs 500 gold, 1 roll per player, up to 2 factions banned

#### Scenario: Template with an override
- **WHEN** a phase plays at 160% and one template overrides the difficulty to 130%
- **THEN** the reply for that template says 130% and 15000 gold, and the reply for the others says 160% and 10000 gold

#### Scenario: Template in several phases
- **WHEN** a template is in the pools of two phases with different settings
- **THEN** the reply gives the settings of each phase separately

#### Scenario: 200% difficulty
- **WHEN** a template is played at 200% difficulty
- **THEN** the reply says there is no gold and no roll, and that the trade is only a toss for color

### Requirement: Unknown names are explained
When the mode is not known, the reply SHALL list the available modes. When the template is not in the mode, the reply SHALL list the templates of that mode.

#### Scenario: Unknown mode
- **WHEN** a player asks about a mode that does not exist
- **THEN** the reply says so and lists the modes that can be looked up

#### Scenario: Template not in the mode
- **WHEN** a player asks about Diamond in El Classico
- **THEN** the reply says Diamond is not in El Classico and lists JC, 6lm10a and h3dm1

### Requirement: Archived modes can be looked up
A mode that is archived SHALL still be found by the info command, and the reply SHALL say that it is archived and cannot start new matches.

#### Scenario: Archived mode
- **WHEN** a player asks about an archived mode
- **THEN** the reply shows its information and says it is archived

### Requirement: Anyone can ask, anywhere, privately
The info command SHALL work in any channel and does not need a match. The reply SHALL be visible only to the player who asked. When the player starts typing, the bot SHALL offer the known modes, and for the template the templates of the chosen mode.

#### Scenario: Outside a match
- **WHEN** a player asks about a mode in an ordinary channel
- **THEN** only that player sees the reply and no thread or match is created

#### Scenario: Autocomplete
- **WHEN** a player has chosen El Classico and starts typing a template
- **THEN** the bot offers JC, 6lm10a and h3dm1

Follow-up, not part of this change: more facts about a template, such as its timer and a link to download it when it is not available in the game.
