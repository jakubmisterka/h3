## ADDED Requirements

### Requirement: A fixed phase has no selection
In a fixed phase the bot SHALL NOT run bans or picks. The games of the match SHALL be the phase's template, as many times as the best-of, in play order.

#### Scenario: BO3 on one template
- **WHEN** a match starts in a fixed best-of-3 phase whose template is Nostalgia
- **THEN** the games are game 1 Nostalgia, game 2 Nostalgia and game 3 Nostalgia, known from the start

#### Scenario: No selection steps
- **WHEN** a fixed phase is in progress
- **THEN** no message asks any player to ban or pick
