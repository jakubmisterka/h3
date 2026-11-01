## ADDED Requirements

### Requirement: A tournament can link to its rules
A format SHALL be able to state `rules_link`, a link to the tournament's full rules, which SHALL start with `https://`. The field is optional. A format with a link that does not start with `https://` SHALL be rejected, with a message naming the field.

#### Scenario: A link
- **WHEN** a format states `rules_link` as `https://example.com/rules`
- **THEN** the format is accepted and the bot knows the link

#### Scenario: No link
- **WHEN** a format states no `rules_link`
- **THEN** the format is accepted and the bot shows no link

#### Scenario: A bad link
- **WHEN** a format states `rules_link` as `example.com/rules`
- **THEN** validation fails and says `rules_link` must be a link starting with https://
