## ADDED Requirements

### Requirement: Mode info links to the tournament's rules
When a tournament states a link to its rules, the reply for the mode SHALL give it on a line of its own right after the description, or after the name when there is no description, as a link with no preview.

#### Scenario: A mode with a link
- **WHEN** a player asks about a mode whose tournament states a link to its rules
- **THEN** the reply has the line "Rules: [full tournament rules](<link>)" near the top

#### Scenario: A mode without a link
- **WHEN** the tournament states none
- **THEN** the reply has no such line
