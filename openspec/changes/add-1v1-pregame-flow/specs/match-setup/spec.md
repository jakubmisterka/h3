# Spec Delta

## Purpose

Covers how a player starts a pre-game match against an opponent: choosing the mode, getting a match thread, the coinflip that decides who is A, and picking the match back up later.

## ADDED Requirements

### Requirement: Player starts a match with mode and opponent
A player SHALL start a match with a slash command that names the mode and the opponent. The bot SHALL trust the command and SHALL NOT check whether either player is entered in a tournament.

#### Scenario: Normal start
- **WHEN** a player starts a match naming a mode and an opponent
- **THEN** the bot creates a match thread, mentions both players in it, and starts the match

#### Scenario: Friendly game in tournament mode
- **WHEN** two players who are not in the tournament start a match in that mode
- **THEN** the match runs normally

#### Scenario: Invalid opponent
- **WHEN** a player names themselves or a bot as the opponent
- **THEN** the bot refuses and no thread is created

### Requirement: Phase is asked only when needed
The bot SHALL ask which phase the match is in only if the chosen mode has more than one phase.

#### Scenario: Multi-phase mode
- **WHEN** a player starts a match in a mode with more than one phase
- **THEN** the bot asks for the phase before continuing

#### Scenario: Single-phase mode
- **WHEN** a player starts a match in a mode with one phase
- **THEN** the match starts with no phase question

### Requirement: Agreed-template modes need a template
If the chosen phase lets players agree on the template, the starting player SHALL name the template, and it SHALL be one of the phase's allowed templates.

#### Scenario: Ranked game with a template
- **WHEN** a player starts a ranked match and names an allowed template
- **THEN** the match goes straight to the trade for that template

#### Scenario: Missing or unknown template
- **WHEN** the template is missing or not allowed in that phase
- **THEN** the bot refuses and lists the allowed templates

### Requirement: The bot does the coinflip
After a match starts, the bot SHALL decide at random which player wins the coinflip and announce the winner in the thread. The winner is A and the other player is B. A acts first in every step that has a first actor.

#### Scenario: Announcement
- **WHEN** the match starts in a sequence mode
- **THEN** the thread says who won the coinflip and that they ban first

#### Scenario: Fair chance
- **WHEN** many matches are started
- **THEN** each player has an equal chance of being A

### Requirement: One thread per match, visibility from the format
Each match SHALL have its own thread. The thread SHALL be public or private according to the format. Several matches SHALL be able to run at the same time without affecting one another.

#### Scenario: Private format
- **WHEN** the format is private
- **THEN** only the two players, the bot and users with thread management can read the thread

#### Scenario: Parallel matches
- **WHEN** two matches run at once
- **THEN** a ban in one does not change the other

### Requirement: The match starts in the current channel
The bot SHALL create the match thread in the channel where the start command was run. The bot SHALL NOT have its own setting for which channels may be used; a server limits the channels through the bot's Discord permissions.

#### Scenario: Any channel
- **WHEN** a player starts a match in a channel where the bot can create threads
- **THEN** the thread is created in that channel

#### Scenario: Channel without access
- **WHEN** a player runs the start command in a channel the server has hidden from the bot
- **THEN** the command is not available there and no match is created

### Requirement: Only the two players act
Commands that change a match SHALL be accepted only from its two players and only inside its thread.

#### Scenario: Outsider
- **WHEN** a user who is not one of the players runs a match command in the thread
- **THEN** the bot refuses and changes nothing

#### Scenario: Command outside a thread
- **WHEN** a player runs a match command outside a match thread
- **THEN** the bot says to use it inside the match thread

### Requirement: A match continues from its thread
The bot SHALL keep no match data outside the thread. After a bot restart, or when players reopen an archived thread, the bot SHALL continue from where the thread left off using only the thread's messages.

#### Scenario: Restart mid-selection
- **WHEN** the bot restarts after two bans and a player runs the next command
- **THEN** the bot knows the two bans and whose turn it is, and continues

#### Scenario: Later trade
- **WHEN** players finish selection and the trade of game 1, leave, and reopen the thread the next day
- **THEN** they can continue with the trade of game 2 without repeating anything

#### Scenario: Message deleted
- **WHEN** a bot message needed to rebuild the match was deleted
- **THEN** the bot says the match cannot be rebuilt and does not guess

Open question: whether slash commands work in an archived thread. This is to be tested on the dev bot. Until then players reopen an archived thread by hand; resuming it automatically is a follow-up idea (see the proposal).
