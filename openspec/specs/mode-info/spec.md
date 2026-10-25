# mode-info Specification

## Purpose
Lets players look up how a tournament mode works and how a template is played in it, without starting a match. It also gives contributors a quick way to check that a new format file says what they meant.

## Requirements

### Requirement: A player can look up a mode
A player SHALL be able to ask for the information about a mode by naming it. The reply SHALL give the mode's name, the templates of the tournament, and for each phase its name, its best-of and the templates in its pool. The mode SHALL be found by its id or its name, ignoring case. Templates SHALL be shown by the name players read (for example Jebus Cross), never by their short id. A reply SHALL NOT repeat itself: a mode with only one phase SHALL NOT mention the phase by name, and a phase that uses all the templates of the tournament SHALL say so instead of listing them again.

#### Scenario: Single-phase mode
- **WHEN** a player asks about Sample Cup, which has one phase
- **THEN** the reply names Sample Cup, says best of 1, and lists the templates Jebus Cross, 6lm10a and h3dm1 once, without naming the phase

#### Scenario: A phase that uses every template
- **WHEN** one phase of a mode with several phases uses all the templates of the tournament
- **THEN** its part of the reply says "Templates: all" instead of listing them again

#### Scenario: Multi-phase mode
- **WHEN** a player asks about a mode with three phases
- **THEN** the reply lists every template of the tournament once, and every phase with its own best-of and its own pool

### Requirement: Mode info says how templates are chosen
For each phase, the reply SHALL say how the template is chosen on one line labelled Template Selection: first the order in which the players act, written the way players write it, one letter per step (A for the coinflip winner, B for the other player) without the decider, such as AB or ABABABBA; then a colon; then the steps in words, naming the player and the action ("A bans", "B picks"), and ending with "then decider" when the sequence has one. For a phase where players agree on the template, it SHALL say so.

#### Scenario: Ban, ban
- **WHEN** a phase has the sequence A ban, B ban, decider
- **THEN** the reply says "AB: A bans, B bans, then decider"

#### Scenario: Bans and picks
- **WHEN** a phase has the sequence A ban, B ban, A pick, B pick, A ban, B ban, B ban, A ban, decider
- **THEN** the reply says "ABABABBA: A bans, B bans, A picks, B picks, A bans, B bans, B bans, A bans, then decider"

#### Scenario: Players acting twice in a row
- **WHEN** a phase has the sequence A ban, B ban, B ban, A ban, A pick, B pick, decider
- **THEN** the reply says "ABBAAB: A bans, B bans, B bans, A bans, A picks, B picks, then decider"

#### Scenario: Both games picked, no decider
- **WHEN** a best-of-2 phase has the sequence A ban, B ban, A pick, B pick and no decider
- **THEN** the reply says "ABAB: A bans, B bans, A picks, B picks"

#### Scenario: Agreed template
- **WHEN** a player asks about a mode where players agree on the template
- **THEN** the reply says the players agree on the template, and lists the templates allowed

### Requirement: A player can look up a template in a mode
A player SHALL be able to ask about one template in a mode. The reply SHALL give the template's difficulty and the roll rules that apply to it (the cost of a roll, the rolls each player has, and the most towns banned per roll), each said once. Where the roll rules differ between the phases that use the template, the reply SHALL give the value most phases use, and then name each phase that differs with only the rules that differ there. A mode with one phase SHALL NOT be mentioned by phase. If the template is played in only some of the phases, the reply SHALL say which.

#### Scenario: Template with the defaults
- **WHEN** a player asks about JC (or Jebus Cross) in Sample Cup
- **THEN** the reply says 160% difficulty and the roll as "500 gold, 1 per player, up to 2 towns banned", with no phase named

#### Scenario: Same in every phase
- **WHEN** a template has the same roll rules in all three phases of a mode
- **THEN** the reply says the difficulty and the roll rules once, and names no phase

#### Scenario: Template with an override for the whole tournament
- **WHEN** the tournament sets a roll cost of 500 and one template is listed with a roll cost of 0
- **THEN** the reply for that template says the roll is free, and the reply for the others says the roll costs 500 gold

#### Scenario: Only the differing rule is listed
- **WHEN** a template has two rolls per player in the final and the usual one in the other phases
- **THEN** the reply gives the usual roll rules once, and one more line "Final: 2 per player"

#### Scenario: Several rules differ in one phase
- **WHEN** in one phase a template has free rolls and no bans
- **THEN** that phase's line lists both, for example "Final: free, no bans"

#### Scenario: The base is the value most phases use
- **WHEN** a template has two rolls per player in two phases and one in the third
- **THEN** the reply gives two rolls as the usual rule and lists only the third phase as different

#### Scenario: Template played in only some phases
- **WHEN** a template is in the pool of the final only
- **THEN** the reply says it is played in the final

#### Scenario: 200% difficulty
- **WHEN** a template is played at 200% difficulty
- **THEN** the reply says there is no roll, and that the trade is only a toss for color

### Requirement: A reply can be limited to one phase
A player SHALL be able to limit a reply to one phase of the mode, by naming it, for a mode or for a template in it. The phase SHALL be found by name, ignoring case. The bot SHALL offer the phases of the chosen mode when the player starts typing, and nothing for a mode with only one phase.

#### Scenario: One phase of a mode
- **WHEN** a player asks about a mode with three phases and names the final
- **THEN** the reply gives the mode's name and templates and only the final's part

#### Scenario: One phase of a template
- **WHEN** a player asks about a template and names a phase that uses it
- **THEN** the reply gives the template's rules in that phase, with the phase named in the title

#### Scenario: A phase that does not use the template
- **WHEN** a player asks about a template in a phase that does not use it
- **THEN** the reply says so and names the phases that do

#### Scenario: Unknown phase
- **WHEN** a player names a phase the mode does not have
- **THEN** the reply says so and lists the phases of the mode

### Requirement: Unknown names are explained
When the mode is not known, the reply SHALL list the available modes. When the template is not in the mode, the reply SHALL list the templates of that mode.

#### Scenario: Unknown mode
- **WHEN** a player asks about a mode that does not exist
- **THEN** the reply says so and lists the modes that can be looked up

#### Scenario: Template not in the mode
- **WHEN** a player asks about Diamond in Sample Cup
- **THEN** the reply says Diamond is not in Sample Cup and lists Jebus Cross, 6lm10a and h3dm1

### Requirement: Archived modes can be looked up
A mode that is archived SHALL still be found by the info command, and the reply SHALL say that it is archived and cannot start new matches.

#### Scenario: Archived mode
- **WHEN** a player asks about an archived mode
- **THEN** the reply shows its information and says it is archived

### Requirement: Anyone can ask, anywhere, privately
The info command SHALL work in any channel and does not need a match. The reply SHALL be visible only to the player who asked. When the player starts typing, the bot SHALL offer the known modes, and for the template the templates of the chosen mode.

#### Scenario: Outside a match
- **WHEN** a player asks about a mode in an ordinary channel
- **THEN** only that player sees the reply and no thread or match is created

#### Scenario: Autocomplete
- **WHEN** a player has chosen Sample Cup and starts typing a template
- **THEN** the bot offers Jebus Cross, 6lm10a and h3dm1 (choosing one fills in its id)

Follow-up, not part of this change: more facts about a template, such as its timer and a link to download it when it is not available in the game.
