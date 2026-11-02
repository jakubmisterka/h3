## ADDED Requirements

### Requirement: The rules at the start of a match link to the tournament's rules
When a tournament states a link to its rules, the rules the bot posts at the start of a match SHALL include it, as one message of its own right after the number of games, as a link with no preview. A tournament that states none gets no such message.

#### Scenario: A tournament with a link
- **WHEN** a match starts in a tournament that states a link to its rules
- **THEN** the message after "Format: BO3" is "Rules: [full tournament rules](<link>)"

#### Scenario: A tournament without a link
- **WHEN** a match starts in a tournament that states none
- **THEN** the rules messages have no line about the rules document
