## ADDED Requirements

### Requirement: The thread names the alternatives of a template
Where the thread says what is played on a game's template at the start of its trade, it SHALL, when the tournament states alternatives for the template, add one line: that by agreement the template can be changed to each alternative, named by its name in code, with a link to download each one that is not built into HotA. This covers the lines posted when `/trade start` opens a game's trade and the rules of a match started with a named template. The line SHALL come after the facts and the trade rule, before the hint to `/info` that closes these lines, and SHALL NOT change anything else: the starting gold, the trade and the lobby settings are those of the template the game was started with.

#### Scenario: An alternative with a download link
- **WHEN** the trade of a game on h3dm1 starts and the tournament states the alternative h3dm1_nc, which has to be downloaded
- **THEN** the thread says "By agreement the template can be changed to `h3dm1_nc` ([download](<link>))" before the hint to `/info`

#### Scenario: An alternative built into HotA
- **WHEN** the alternative is built into HotA
- **THEN** the line names it and has no link

#### Scenario: Several alternatives
- **WHEN** a template has two alternatives
- **THEN** one line names both joined by "or", each with its link where it has one

#### Scenario: No alternatives
- **WHEN** the tournament states no alternative for the template
- **THEN** no line about alternatives is posted

#### Scenario: The match is unchanged
- **WHEN** the players agree to play the alternative
- **THEN** the bot is not told, and the starting gold and the lobby settings are those of the template of the game
