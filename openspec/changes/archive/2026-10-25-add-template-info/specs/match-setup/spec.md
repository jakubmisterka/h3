# Spec Delta

## ADDED Requirements

### Requirement: The thread says what is played on a game's template
Whenever the thread announces the template a game is played on before its trade, the bot SHALL also give, each on a short line, what is played on that template in the match's phase, as far as it is stated: that it is a mirror template, where to get it, the timer in its compact form (as it is typed into the lobby), the map size, the roads, the computer players and the recommended length of simultaneous turns. This covers the rules messages at the start of a match with a named template, and the message that announces a game once a pick, or the last ban for the decider's game, has settled it. A fact that is not stated SHALL get no line.

#### Scenario: A named template at the start
- **WHEN** a match starts with a named template whose timer is `12:00+06:00+02:00`, which has to be downloaded and has 6 computer players
- **THEN** the rules messages include "Timer: 12:00+06:00+02:00", the download link and "AI players: 6"

#### Scenario: What the phase chose
- **WHEN** the match is in a phase where the tournament chose the map size `XL+U` for the template
- **THEN** the line says "Map: XL+U" and not the template's default

#### Scenario: A game decided by a pick
- **WHEN** A picks a template with a timer and the pick settles game 1
- **THEN** the message that announces game 1 gives the template and the facts that are stated, and says its trade can be started

#### Scenario: The decider's game
- **WHEN** the last ban settles the decider's game
- **THEN** the message that announces that game gives the stated facts in the same way

#### Scenario: Nothing stated
- **WHEN** a game's template states none of the facts and the tournament sets no timer
- **THEN** the announcement is the same as before this change
