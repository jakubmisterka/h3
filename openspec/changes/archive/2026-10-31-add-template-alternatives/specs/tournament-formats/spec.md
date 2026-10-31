## ADDED Requirements

### Requirement: A tournament can state alternatives for a template
A tournament SHALL be able to state, for a template, a list of alternatives: other templates of the catalogue that the players may play instead, by agreement. The setting is stacked like the other settings of a template (the tournament's list, then a phase's pool, the most specific winning). Every alternative SHALL be a template of the catalogue, different from the template it is an alternative to, listed once, and either built into HotA or with a download link. A format that breaks this SHALL be rejected, with a message naming the template and the alternative.

#### Scenario: An alternative
- **WHEN** a tournament lists h3dm1 with the alternative h3dm1_nc, and h3dm1_nc is in the catalogue with a download link
- **THEN** the format is accepted

#### Scenario: An alternative that is not in the catalogue
- **WHEN** a tournament names an alternative that the catalogue does not have
- **THEN** validation fails and names the template and the unknown alternative

#### Scenario: An alternative that cannot be obtained
- **WHEN** an alternative is neither built into HotA nor has a download link
- **THEN** validation fails and says the alternative needs a link to download it

#### Scenario: The template itself
- **WHEN** a template is listed as its own alternative, or an alternative is listed twice
- **THEN** validation fails and says so

#### Scenario: A phase states its own
- **WHEN** a template has the alternative h3dm1_nc in the tournament's list and another in the pool of one phase
- **THEN** the phase's alternatives replace the tournament's for that phase
