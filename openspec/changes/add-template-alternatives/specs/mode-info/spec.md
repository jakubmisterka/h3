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
