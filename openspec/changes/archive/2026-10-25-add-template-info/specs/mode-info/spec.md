# Spec Delta

## MODIFIED Requirements

### Requirement: A player can look up a mode
A player SHALL be able to ask for the information about a mode by naming it. The reply SHALL give the mode's name, the templates of the tournament, and for each phase its name, its best-of and the templates in its pool. The mode SHALL be found by its id or its name, ignoring case. Templates SHALL be shown by the name players read (for example Jebus Cross), never by their short id. A reply SHALL NOT repeat itself: a mode with only one phase SHALL NOT mention the phase by name, and a phase that uses all the templates of the tournament SHALL say so instead of listing them again. When the tournament states a description or additional rules, the reply SHALL give them too.

#### Scenario: Single-phase mode
- **WHEN** a player asks about Sample Cup, which has one phase
- **THEN** the reply names Sample Cup, says best of 1, and lists the templates Jebus Cross, 6lm10a and h3dm1 once, without naming the phase

#### Scenario: A phase that uses every template
- **WHEN** one phase of a mode with several phases uses all the templates of the tournament
- **THEN** its part of the reply says "Templates: all" instead of listing them again

#### Scenario: Multi-phase mode
- **WHEN** a player asks about a mode with three phases
- **THEN** the reply lists every template of the tournament once, and every phase with its own best-of and its own pool

#### Scenario: A tournament with a description and additional rules
- **WHEN** a player asks about a mode that states a description and additional rules
- **THEN** the reply gives the description and the additional rules, each on its own line

#### Scenario: A tournament with neither
- **WHEN** a player asks about a mode that states no description and no additional rules
- **THEN** the reply is the same as before this change

### Requirement: A player can look up a template in a mode
A player SHALL be able to ask about one template in a mode. The reply SHALL give the template's difficulty and the roll rules that apply to it (the cost of a roll, the rolls each player has, and the most towns banned per roll), each said once. Where the roll rules differ between the phases that use the template, the reply SHALL give the value most phases use, and then name each phase that differs with only the rules that differ there. A mode with one phase SHALL NOT be mentioned by phase. If the template is played in only some of the phases, the reply SHALL say which. The reply SHALL also give, each on a short line, what is played on the template in that mode, as far as it is stated: that it is a mirror template, where to get it, the timer, the map size, the roads, the computer players and the recommended length of simultaneous turns. These follow the same rule as the roll rules where phases differ. A fact that is not stated SHALL NOT appear, and nothing SHALL be guessed in its place. The reply SHALL also give the template's description and its additional rules (the rules that apply in that mode, after the tournament's choices) when they are stated.

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

#### Scenario: What is played, from the template's defaults
- **WHEN** a player asks about a template whose defaults are map size `L+U`, roads `mid` and 3 computer players, in a mode that chooses nothing for it
- **THEN** the reply has the lines "Map: L+U", "Roads: mid" and "AI players: 3"

#### Scenario: What the tournament chose
- **WHEN** the mode chooses the map size `XL+U` for the template
- **THEN** the reply says "Map: XL+U" and not the template's default

#### Scenario: The timer
- **WHEN** a player asks about a template in a mode whose timer is `12:00+06:00+02:00`
- **THEN** the reply has the line "Timer: 12:00+06:00+02:00" and does not spell the timer out

#### Scenario: A setting that differs between phases
- **WHEN** a template is played on `L+U` in the groups and on `XL+U` in the final
- **THEN** the reply gives "Map: L+U" and one more line "Final: XL+U"

#### Scenario: Where to get it
- **WHEN** a player asks about a template that states a download link, and about one that is built into HotA
- **THEN** the first reply says "Download:" with the link and the second says it is built into HotA

#### Scenario: Roads and computer players
- **WHEN** a player asks about templates with roads `slow+mid`, with roads `none`, with 6 computer players and with 0
- **THEN** the replies say "Roads: slow+mid", "No roads", "AI players: 6" and "No AI players"

#### Scenario: Simultaneous turns
- **WHEN** a player asks about a template whose recommended simultaneous turns are `117`
- **THEN** the reply says "Sim turns until 117"

#### Scenario: A mirror template
- **WHEN** a player asks about a mirror template
- **THEN** the reply says both players get the same town

#### Scenario: Description and rules
- **WHEN** a player asks about a template that states a description and additional rules
- **THEN** the reply gives the description and the additional rules, each on its own line

#### Scenario: Rules the tournament changed
- **WHEN** the tournament gives the template other additional rules than the catalogue states
- **THEN** the reply gives the tournament's rules and not the catalogue's

#### Scenario: Rules that differ between phases
- **WHEN** the groups have other additional rules for a template than the final
- **THEN** the reply gives the additional rules most phases use and one more line for the phase that differs

#### Scenario: Nothing stated
- **WHEN** a player asks about a template that states none of these facts, in a mode that sets no timer
- **THEN** the reply is the same as before this change
