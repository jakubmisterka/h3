# Spec Delta

## MODIFIED Requirements

### Requirement: Final lobby settings
When the color section is done, the bot SHALL post the lobby settings for the game as one message: game number, template, each player's town, color and gold difference from the starting gold, and the settings typed into the lobby as far as they are stated: the timer, the map size, the roads and the computer players.

#### Scenario: Summary
- **WHEN** the last section of game 1 is reported
- **THEN** the thread shows template JC, P1 Necropolis with gold +400, and P2 Tower with gold -400, each with their color

#### Scenario: Summary with the lobby settings
- **WHEN** the last section of a game is reported, and its timer is `12:00+06:00+02:00`, its map size `L+U`, its roads `mid` and it has 3 computer players
- **THEN** the lobby settings include "Timer: 12:00+06:00+02:00", "Map: L+U", "Roads: mid" and "AI players: 3" with the other settings

#### Scenario: Summary without them
- **WHEN** nothing is stated for the game's template and the tournament sets no timer
- **THEN** the lobby settings have none of these lines

## ADDED Requirements

### Requirement: The thread gives the additional rules when a game's trade starts
When the trade of a game is opened for the first time, the bot SHALL post the additional rules of the game's template, as they apply in the match's phase, as a message of their own, if there are any. The rules SHALL NOT be posted again when a closed trade is reopened, and a template without additional rules SHALL get no such message.

#### Scenario: A trade starts
- **WHEN** the trade of a game on a template with additional rules starts
- **THEN** the thread gets the rules, after the opening of the trade

#### Scenario: The rules of the phase
- **WHEN** the tournament gives the template other additional rules in this phase
- **THEN** the thread gets those rules

#### Scenario: A trade is reopened
- **WHEN** a closed trade of that game is started again
- **THEN** the rules are not posted again

#### Scenario: No additional rules
- **WHEN** the trade of a game on a template without additional rules starts
- **THEN** the thread has no message about rules
