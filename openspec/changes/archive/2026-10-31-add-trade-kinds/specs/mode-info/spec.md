## ADDED Requirements

### Requirement: The template reply says how its trade is run
The reply about a template in a mode SHALL say how its trade is run when it is not the standard trade: with computer-player packs, or a roulette with the number of hero bans each player may make and whether the heroes are drawn after the rolls. A mirror trade is said by the line that already says the template is a mirror. When the kind differs between phases, the reply SHALL give the kind most phases use and name the phases that differ, as it does for the other settings. A standard trade SHALL get no line.

#### Scenario: Packs
- **WHEN** a player asks about a template whose trade has computer-player packs
- **THEN** the reply says "Trade: computer-player packs"

#### Scenario: A roulette
- **WHEN** a player asks about a template traded as a roulette with 1 hero ban
- **THEN** the reply says "Trade: roulette, 1 hero ban each, heroes drawn after the rolls"

#### Scenario: Different in one phase
- **WHEN** the final trades the template as a roulette and the groups trade it as a standard trade
- **THEN** the reply gives the roulette line for the final only, naming the phase

#### Scenario: A standard trade
- **WHEN** a player asks about a template with a standard trade in every phase
- **THEN** the reply has no line about the trade
