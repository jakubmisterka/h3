## RENAMED Requirements

- FROM: `### Requirement: Template choice is either a sequence or agreed`
- TO: `### Requirement: Template choice is a sequence, agreed, or fixed`

## MODIFIED Requirements

### Requirement: Template choice is a sequence, agreed, or fixed
A phase SHALL choose templates in one of three ways: by an ordered sequence of steps; by agreement, where the players name the template themselves; or as fixed, where the phase has one template and every game of the match is played on it. A step is a ban or a pick by a named player (A or B), or the decider: the template that is left, which no player chooses. A is the coinflip winner and B is the other player.

#### Scenario: Sequence format
- **WHEN** a phase has the sequence A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban, decider
- **THEN** the bot runs exactly those steps in that order, and the decider takes the one template that is left

#### Scenario: Agreed format
- **WHEN** a phase is marked as agreed, as in ranked mode
- **THEN** no bans or picks happen and the players supply the template when starting the match

#### Scenario: Fixed format
- **WHEN** a best-of-3 phase is marked as fixed and its only template is Nostalgia
- **THEN** no bans or picks happen, the players name no template, and all three games are played on Nostalgia

## ADDED Requirements

### Requirement: A fixed phase has exactly one template
A format file SHALL be rejected when a fixed phase does not have exactly one template, counting the phase's `pool` when it has one and the tournament's template list otherwise. A fixed phase SHALL have no `steps`.

#### Scenario: One template in the tournament
- **WHEN** a tournament lists one template and has a fixed best-of-3 phase
- **THEN** validation passes

#### Scenario: A pool of one
- **WHEN** a tournament lists four templates and a fixed phase has a `pool` with one of them
- **THEN** validation passes, and that phase plays all its games on that template

#### Scenario: More than one template
- **WHEN** a fixed phase has no `pool` and the tournament lists two templates
- **THEN** validation fails and says a fixed phase needs exactly one template, naming the phase

#### Scenario: Steps in a fixed phase
- **WHEN** a fixed phase also has `steps`
- **THEN** validation fails and says a fixed phase has no steps
