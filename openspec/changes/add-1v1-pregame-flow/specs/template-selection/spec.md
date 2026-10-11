# Spec Delta

## Purpose

Describes how two players turn a template pool into the games they will play, by taking turns banning and picking templates in the order the tournament format prescribes.

## ADDED Requirements

### Requirement: Steps follow the format's sequence
The bot SHALL run the ban and pick steps exactly in the order of the format, with A (coinflip winner) and B as named in each step. The bot SHALL announce the current step and the acting player before each step.

#### Scenario: Biggest tournament knockout
- **WHEN** the sequence is A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban
- **THEN** the thread announces each step in that order, naming the acting player

#### Scenario: Seven-template BO3
- **WHEN** the sequence is A ban, B ban, B ban, A ban, A pick, B pick
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
When the last step is done, the one remaining template SHALL become the decider. The bot SHALL announce the games in the order the format states, each with its template.

#### Scenario: BO3 result
- **WHEN** A picked JC, B picked Diamond and h3dm1 is left, and the order is A's pick, B's pick, decider
- **THEN** the bot announces game 1 JC, game 2 Diamond and game 3 h3dm1

#### Scenario: BO1 result
- **WHEN** a BO1 phase ends with one template left
- **THEN** the bot announces that template as the only game

### Requirement: Agreed templates skip selection
In an agreed-template phase the bot SHALL post the template named at the start and go straight to the trade.

#### Scenario: Ranked
- **WHEN** a ranked match starts with a template
- **THEN** no bans or picks are asked and game 1 uses that template

Open question: how to correct a ban or pick made by mistake. In this change a step cannot be undone, and players should ask an organiser. A rewind with the opponent's consent is a follow-up idea (see the proposal).
