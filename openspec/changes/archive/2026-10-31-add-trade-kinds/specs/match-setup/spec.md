## ADDED Requirements

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

## MODIFIED Requirements

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
