## ADDED Requirements

### Requirement: The template reply names its alternatives
The reply for a template in a mode SHALL name the alternatives the tournament states for it in each phase (as the other settings are), each with its download link where it is not built into HotA, and say they can be played instead by agreement. A template without alternatives gets no such line.

#### Scenario: An alternative
- **WHEN** a player asks about h3dm1 in a mode that states the alternative h3dm1_nc
- **THEN** the reply says that by agreement `h3dm1_nc` can be played instead, with its download link

#### Scenario: Alternatives that differ by phase
- **WHEN** the alternatives of a template differ between phases
- **THEN** the reply names the usual ones once and the phase with different ones on its own line, as for the other settings

#### Scenario: No alternatives
- **WHEN** a template has none
- **THEN** the reply has no line about alternatives

### Requirement: A player can look up an alternative of a mode
An alternative a mode states for one of its templates SHALL be accepted as the template of `/info`, and offered while the template is typed, marked as an alternative. The reply SHALL say which template or templates it can replace, by agreement, that the match keeps the settings of the template it was started with, and what the catalogue states about it (that it is a mirror, where to get it, the map size, roads, computer players and the recommended simultaneous turns).

#### Scenario: Looking up an alternative
- **WHEN** a player asks `/info` for the template h3dm1 in a mode where h3dm_nc has h3dm1 as its alternative
- **THEN** the reply says h3dm1 is an alternative to h3dm_nc that can be played instead by agreement, and gives what is known about h3dm1

#### Scenario: Offered while typing
- **WHEN** a player types the template of `/info` for that mode
- **THEN** h3dm1 is offered, marked as an alternative

#### Scenario: A template that is neither played nor an alternative
- **WHEN** a player asks about a template that the mode neither lists nor states as an alternative
- **THEN** the reply says it is not in the mode and lists the mode's templates
