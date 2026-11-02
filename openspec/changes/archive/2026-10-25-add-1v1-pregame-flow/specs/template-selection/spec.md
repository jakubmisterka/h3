# Spec Delta

## Purpose

Describes how two players turn a template pool into the games they will play, by taking turns banning and picking templates in the order the tournament format prescribes.

## ADDED Requirements

### Requirement: Steps follow the format's sequence
The bot SHALL run the ban and pick steps exactly in the order of the format, with A (coinflip winner) and B as named in each step. The bot SHALL announce the current step and the acting player before each step.

#### Scenario: Biggest tournament knockout
- **WHEN** the sequence is A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban, decider
- **THEN** the thread announces each player's step in that order, naming the acting player, and then the decider

#### Scenario: Seven-template BO3
- **WHEN** the sequence is A ban, B ban, B ban, A ban, A pick, B pick, decider
- **THEN** B acts twice in a row at steps 2 and 3, and the bot announces both

### Requirement: Only the acting player acts, on a valid template
A ban or pick SHALL be accepted only from the player whose step it is, and only for a template still in the pool. The bot SHALL offer only remaining templates when a player starts typing.

#### Scenario: Wrong player
- **WHEN** B tries to ban while it is A's step
- **THEN** the bot refuses, names whose step it is, and changes nothing

#### Scenario: Wrong action
- **WHEN** a player tries to pick during a ban step
- **THEN** the bot refuses and says a ban is expected

#### Scenario: Template already gone
- **WHEN** a player names a banned, picked or unknown template
- **THEN** the bot refuses and shows the remaining templates

### Requirement: Remaining pool is always visible
After each step, the bot SHALL post the remaining pool and the templates banned and picked so far.

#### Scenario: After a ban
- **WHEN** A bans mt_nebula in a 9-template pool
- **THEN** the thread shows 8 remaining templates and that A banned mt_nebula

### Requirement: Selection ends with the ordered games
A decider step SHALL take the one remaining template without any player acting. When the sequence is done, the bot SHALL announce the games in play order, each with its template: the picks in the order they were made, then the decider if the sequence has one.

#### Scenario: BO3 result
- **WHEN** A picked JC, B picked Diamond and the decider takes h3dm1
- **THEN** the bot announces game 1 JC, game 2 Diamond and game 3 h3dm1

#### Scenario: BO1 result
- **WHEN** a BO1 phase with the sequence ban, ban, decider is done
- **THEN** the bot announces the template the decider took as the only game

#### Scenario: No decider
- **WHEN** a best-of-2 phase ends after A's pick and B's pick, with no decider step
- **THEN** the bot announces the two picks as game 1 and game 2

### Requirement: A named template skips selection
When a match starts with a named template, whether the phase lets players agree on it or chooses templates by bans and picks, the bot SHALL post the template and go straight to the trade, and SHALL NOT run the bans and picks.

#### Scenario: Ranked
- **WHEN** a ranked match starts with a template
- **THEN** no bans or picks are asked and game 1 uses that template

#### Scenario: Bans and picks skipped
- **WHEN** a match in a phase with bans and picks starts with a template from its pool
- **THEN** no bans or picks are asked and game 1 uses that template

A ban or pick made by mistake is corrected with the undo of the `match-setup` capability: both players agree to go back to before that record.
