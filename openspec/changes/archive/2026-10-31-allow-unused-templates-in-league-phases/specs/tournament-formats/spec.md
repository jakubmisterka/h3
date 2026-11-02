## MODIFIED Requirements

### Requirement: Format files are validated
A format file SHALL be rejected, with a message naming the problem, unless: for a sequence phase the pool holds exactly as many templates as the sequence has steps, because each template is banned, picked or the decider, or, when the sequence has no decider, at least as many, because the templates that are neither banned nor picked are not played; the decider, if there is one, is the last step and names no player; the picks plus the decider, if there is one, make as many games as the best-of; every template is known; and the file has all required fields.

#### Scenario: Pool does not fit the sequence
- **WHEN** a phase has a pool of 9 templates and a sequence of 7 steps that ends with a decider
- **THEN** validation fails and says the pool must have as many templates as the sequence has steps

#### Scenario: Valid BO1 group stage
- **WHEN** a phase has best-of 1, a pool of 3 templates and the sequence A ban, B ban, decider
- **THEN** validation passes and the decider takes the remaining template, which is the only game

#### Scenario: A league phase with templates left over
- **WHEN** a best-of-2 phase has a pool of 7 templates and the sequence A ban, B ban, A pick, B pick with no decider
- **THEN** validation passes, the games are A's pick and B's pick, and the other three templates are not played

#### Scenario: A pool smaller than the sequence
- **WHEN** a phase with no decider has a pool of 3 templates and a sequence of 4 steps
- **THEN** validation fails and says the pool needs at least as many templates as the sequence has steps

#### Scenario: Wrong number of games
- **WHEN** a phase has best-of 3 and the sequence A ban, B ban, decider
- **THEN** validation fails and says a best-of-3 needs 3 games and the sequence gives 1

#### Scenario: Decider in the wrong place
- **WHEN** the decider is not the last step, or it names a player
- **THEN** validation fails with a message naming the problem

#### Scenario: Unknown template
- **WHEN** a phase's pool names a template that is not in the catalogue
- **THEN** validation fails and names the template

#### Scenario: Missing required field
- **WHEN** a format file has no phases
- **THEN** validation fails and names the missing field
