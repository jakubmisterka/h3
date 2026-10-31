# match-setup Specification

## Purpose
Covers how a player starts a pre-game match against an opponent: choosing the mode, getting a match thread, the coinflip that decides who is A, and picking the match back up later.

## Requirements

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

### Requirement: The thread says what is played on a game's template
Whenever the thread announces the template a game is played on before its trade, the bot SHALL also say, each as a short message of its own and only as far as it is stated, what players need to start: where to get the template when it is not built into HotA, as a link; the timer in its compact form (as it is typed into the lobby); the recommended length of simultaneous turns; and how the template's trade is run, with one message for each kind of trade. It SHALL also say how to find out more with the `/info` command. It SHALL NOT repeat the map size, the roads, the computer players or that the template is a mirror: players know them, and `/info` and the lobby settings give them. This covers the rules messages at the start of a match with a named template, and the message posted when `/trade start` opens a game's trade after a pick (or the decider). The message that announces a game once a pick, or the last ban for the decider's game, has settled it SHALL be only the game with how to start its trade, then (as a second line) how to find out more with `/info`, so that it cannot read as being about the game that was just traded. A fact that is not stated SHALL get no line.

#### Scenario: A named template at the start
- **WHEN** a match starts with a named template whose timer is `12:00+06:00+02:00` and whose sim turns are `117`, and which has to be downloaded
- **THEN** the rules messages include "Timer: `12:00+06:00+02:00`", "Sim turns: `117`", a link to download the template and how its trade is run

#### Scenario: A template that is not built in
- **WHEN** the template states a download link instead of being built into HotA
- **THEN** the rules say it is not built into HotA and give the link

#### Scenario: A built-in template
- **WHEN** the template is built into HotA
- **THEN** there is no message about where to get it

#### Scenario: What the phase chose
- **WHEN** the match is in a phase where the tournament chose the timer for the template
- **THEN** the message gives that timer and not the tournament's

#### Scenario: Only what is needed
- **WHEN** the template states a map size, roads, computer players and that it is a mirror
- **THEN** the rules messages say none of them

#### Scenario: How to find out more
- **WHEN** a match starts with a named template
- **THEN** one message says how to use `/info` for this mode and template

#### Scenario: A game decided by a pick
- **WHEN** A picks a template with a timer and the pick settles game 1
- **THEN** the message that announces game 1 gives how to find out more and says its trade can be started, and `/trade start` then posts the facts that are stated and how the trade is run, before the opening of the trade

#### Scenario: The decider's game
- **WHEN** the last ban settles the decider's game
- **THEN** the message that announces that game is short in the same way, and its facts come when its trade starts

#### Scenario: Nothing stated
- **WHEN** a game's template states no timer, no sim turns and no download link
- **THEN** the message posted when its trade starts has only how the trade is run

### Requirement: The match thread opens in a few short messages
The first messages of a match thread SHALL be short, and laid out on lines. The record that starts the match SHALL give the two players, then the mode, the phase and, when it was named, the template, each on its own line. The rules that follow SHALL say how many games the match has as "Format: " and "BO" and the number (Format: BO1, BO3, BO5). They SHALL NOT say the template again when the record has it, and SHALL NOT say who A and B are before the coinflip, since the coinflip says it. A match thread SHALL NOT say "This is your match thread".

#### Scenario: The record of the start
- **WHEN** a match starts in El Classico, phase Main, with the template h3dm1
- **THEN** the record gives the players on the first line and the mode, the phase and the template each on a line of their own

#### Scenario: The number of games
- **WHEN** a match starts with a named template
- **THEN** the rules say "Format: BO1" and do not repeat the template, which the start record already has

#### Scenario: The number of games of a mode
- **WHEN** a match starts in a phase that is a best of 3 with bans and picks
- **THEN** the rules say "Format: BO3"

#### Scenario: No explanation before the coinflip
- **WHEN** a match starts
- **THEN** no message before the coinflip says who A and B will be

### Requirement: A match in a fixed phase plays every game on the phase's template
In a fixed phase the starting player SHALL NOT need to name a template. The bot SHALL take the phase's only template, post the rules of the match (the format as BO and the number of games, the template as code, and what is stated about the template, as for a match with a named template), do the coinflip and open the trade of game 1 itself. The match SHALL have as many games as the best-of of the phase, all on that template. When the trade of a game is done, the bot SHALL say which game is next and how to start its trade, until every game has been traded, and then say that every game is traded. A player who names the phase's template SHALL get the same match. A player who names another template SHALL be refused, with the template of the phase listed. The ban and pick commands SHALL say that this phase has no bans or picks.

#### Scenario: Start without a template
- **WHEN** a player starts a match in a fixed best-of-3 phase and names no template
- **THEN** the thread says "Format: BO3", "Template: `Nostalgia`" and what is stated about the template, the coinflip is done and the trade of game 1 is opened

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

### Requirement: The thread names the alternatives of a template
Where the thread says what is played on a game's template at the start of its trade, it SHALL, when the tournament states alternatives for the template, add one line: that by agreement the template can be changed to each alternative, named by its name in code, with a link to download each one that is not built into HotA. This covers the lines posted when `/trade start` opens a game's trade and the rules of a match started with a named template. The line SHALL come after the facts and the trade rule, before the hint to `/info` that closes these lines, and SHALL NOT change anything else: the starting gold, the trade and the lobby settings are those of the template the game was started with.

#### Scenario: An alternative with a download link
- **WHEN** the trade of a game on h3dm1 starts and the tournament states the alternative h3dm1_nc, which has to be downloaded
- **THEN** the thread says "By agreement the template can be changed to `h3dm1_nc` ([download](<link>))" before the hint to `/info`

#### Scenario: An alternative built into HotA
- **WHEN** the alternative is built into HotA
- **THEN** the line names it and has no link

#### Scenario: Several alternatives
- **WHEN** a template has two alternatives
- **THEN** one line names both joined by "or", each with its link where it has one

#### Scenario: No alternatives
- **WHEN** the tournament states no alternative for the template
- **THEN** no line about alternatives is posted

#### Scenario: The match is unchanged
- **WHEN** the players agree to play the alternative
- **THEN** the bot is not told, and the starting gold and the lobby settings are those of the template of the game
