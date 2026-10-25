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

### Requirement: A match can start straight at the trade with a named template
The starting player SHALL be able to name a template when starting a match. The template SHALL be one of the templates the chosen phase uses (its pool). If the phase lets players agree on the template, naming one is required. A named template makes a match of one game: there are no bans or picks, the bot says which template is played and opens the trade of that game itself, so the players do not need a command first, with the roll rules and allowed towns of that phase. When that trade is done there is nothing more to do in the match: the bot says it was the only game, and another game needs a new match.

#### Scenario: Ranked game with a template
- **WHEN** a player starts a ranked match and names an allowed template
- **THEN** the match goes straight to the trade for that template, and the bot opens it

#### Scenario: Missing template where players agree
- **WHEN** a player starts a match in a phase where the players agree on the template and names none
- **THEN** the bot refuses and lists the allowed templates

#### Scenario: Template named where bans and picks would choose
- **WHEN** a player starts a match in a phase with bans and picks and names a template from its pool
- **THEN** the match has that one game, no ban or pick is asked, and the bot opens the trade of the game: the pair is drawn and the first section is announced

#### Scenario: Template not in the pool
- **WHEN** a player names a template that the phase does not use
- **THEN** the bot refuses, creates no thread and lists the templates the phase uses

#### Scenario: Bans in a match with a named template
- **WHEN** a player uses the ban or pick command in a match that started with a named template
- **THEN** the bot says this match has no bans or picks

#### Scenario: The only game is done
- **WHEN** the trade of a match with a named template is finished
- **THEN** after the lobby settings the bot says that was the only game and that another game needs a new match, and the trade cannot be started again

#### Scenario: The overview
- **WHEN** a player asks for the status of a match with a named template in a best-of-3 phase
- **THEN** the overview shows one game, the named template, and no template selection

### Requirement: The bot does the coinflip
After a match starts, the bot SHALL decide at random which player wins the coinflip and announce the winner in the thread. The winner is A and the other player is B. A acts first in every step that has a first actor.

#### Scenario: Announcement
- **WHEN** the match starts in a sequence mode
- **THEN** the thread says who won the coinflip and that they ban first

#### Scenario: The rules of the phase are stated
- **WHEN** the match starts
- **THEN** the thread states the rules of the phase before the coinflip, one message for each: the best-of, the Template Selection in the short way players write it (for example "AB"), what that means in words ("A bans, B bans, then decider"), that the winner of the coinflip will be player A, and the templates of the phase (or the template the players agreed on, in place of the selection)
- **AND** the coinflip is posted last

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

### Requirement: Either player can ask to undo, and the other must agree
A player SHALL be able to ask to undo the match from a record number (the `8` in a tag like `[#8 tb g1]`): that record and every record after it stop counting, whatever kind of step they are (bans, picks, trades, rolls, skipped rolls, bids), so the match is exactly as it was before record 8. Without a number the latest step SHALL be undone. The records the bot posted when the match started, the start and the coinflip, SHALL NOT be undoable. The bot SHALL post which step the request starts from and that everything after it stops counting too, and point to the match status for where the match stands. The undo SHALL happen only when the other player agrees, which they do by running the undo command without a number (naming the same number also works). A request SHALL lapse when anything else is posted after it. Nothing SHALL be deleted: the request and the undo are records of their own, and the history stays in the thread.

#### Scenario: Asking
- **WHEN** a player asks to undo from record 8
- **THEN** the bot says what record 8 is, that everything after it stops counting too, that the match status shows where the match stands, and that the other player must run the undo command to agree

#### Scenario: Confirming
- **WHEN** the other player runs the undo command without a number right after, or with the same number
- **THEN** the match is exactly as it was before record 8, the bot says so, shows where the match stands, and says what the players can do next (the next ban or pick, the open trade's next section, or the trade that can be started)

#### Scenario: Latest step by default
- **WHEN** a player asks to undo without a number
- **THEN** the request covers only the latest step

#### Scenario: Later steps go too
- **WHEN** a ban is record 5, the trade of game 1 started in record 8, and a player asks to undo from 5
- **THEN** the request says the steps after the ban go too, and once confirmed neither the ban nor the trade count

#### Scenario: A roll can be undone
- **WHEN** both players agree to undo from a roll
- **THEN** the roll, the pair it drew and the payment stop counting

#### Scenario: The same player twice
- **WHEN** the player who asked runs the undo command again
- **THEN** the bot says it is waiting for the other player and changes nothing

#### Scenario: A request that went stale
- **WHEN** something is posted after a request and then the other player runs the undo command
- **THEN** the bot treats it as a new request for the latest step instead of an undo

#### Scenario: Another record number replaces the request
- **WHEN** a request is waiting and either player runs the undo command naming a different record
- **THEN** the new request replaces the old one, the bot says so, and only the new one can be agreed to (by the player who did not make it)

#### Scenario: Not a step
- **WHEN** a player names a record that is not a step or does not exist
- **THEN** the bot refuses and points to the match status

#### Scenario: Already undone
- **WHEN** a player names a record that was already undone
- **THEN** the bot says that record was already undone and points to the match status, which marks the undone records

#### Scenario: The start cannot be undone
- **WHEN** a player names the record of the match start or of the coinflip
- **THEN** the bot refuses and says the start of the match cannot be undone

#### Scenario: Nothing to undo
- **WHEN** a player asks to undo before any step was taken
- **THEN** the bot says there is nothing to undo

#### Scenario: Starting again after an undo
- **WHEN** a ban is undone and the player bans another template
- **THEN** the new ban counts, and the numbering carries on after the undo

Open question: whether slash commands work in an archived thread. This has not been tested. A match thread stays open for 7 days of silence, which is assumed to be enough; if players do run into archived threads, they reopen them by hand, and resuming one automatically is a follow-up idea (see the proposal).
