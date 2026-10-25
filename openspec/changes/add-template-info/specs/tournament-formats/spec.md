# Spec Delta

## ADDED Requirements

### Requirement: A template states its roads, map size and computer players with a default and what is allowed
The template catalogue SHALL allow a template to state its roads, map size and computer players, each as a default and a list of allowed values. Roads are `none`, or one or more of `slow`, `mid` and `fast` joined by `+` in that order (the game's dirt, gravel and cobblestone roads). A map size is `S`, `M`, `L`, `XL`, `H`, `XH` or `G`, with `+U` when played with underground. Computer players are a number from 0 to 6. The default SHALL be one of the allowed values, and no value SHALL be listed twice. A fact that is not stated is unknown. A mistake SHALL stop the bot from starting, with a message that names the entry and the field.

#### Scenario: Roads with a default and what is allowed
- **WHEN** a template states roads with the default `mid` and the allowed values `slow`, `mid`, `fast` and `none`
- **THEN** the catalogue is accepted and the template is known to be played on mid roads unless a tournament chooses another allowed value

#### Scenario: More than one road type
- **WHEN** a template states `slow+mid` as an allowed value of its roads
- **THEN** the catalogue is accepted and that value means slow and mid roads together

#### Scenario: A map size with underground
- **WHEN** a template states the map size default `L+U` with the allowed values `L` and `L+U`
- **THEN** the catalogue is accepted

#### Scenario: Computer players
- **WHEN** a template states computer players with the default 3 and the allowed values 0, 3 and 6
- **THEN** the catalogue is accepted

#### Scenario: A default that is not allowed
- **WHEN** a template states the map size default `XL` with the allowed values `M` and `L`
- **THEN** the bot does not start, and the message says the default must be one of the allowed values

#### Scenario: A value that does not exist
- **WHEN** a template states a road setting `paved`, a map size `XXL` or `L+X`, or 7 computer players
- **THEN** the bot does not start, and the message lists the values there are

#### Scenario: A value listed twice
- **WHEN** a template lists the map size `M` twice among its allowed values
- **THEN** the bot does not start, and the message names the value listed twice

#### Scenario: Nothing stated
- **WHEN** a template states none of these facts
- **THEN** the catalogue is accepted and they are unknown for that template

### Requirement: A mirror template is always played with underground
The template catalogue SHALL allow a template to say it is a mirror template (`mirror` is true), which means both players play the same town. Every map size a mirror template states, the default and the allowed ones, SHALL have `+U`, so that both players can have the same map. A template that does not say it is a mirror is an ordinary template.

#### Scenario: A mirror template
- **WHEN** a template states `mirror` as true and its map sizes are `L+U` and `XL+U`
- **THEN** the catalogue is accepted and the template is known to be a mirror

#### Scenario: A mirror without underground
- **WHEN** a template states `mirror` as true and an allowed map size `L`
- **THEN** the bot does not start, and the message says a mirror template is always played with underground

#### Scenario: An ordinary template
- **WHEN** a template does not state `mirror`
- **THEN** it is an ordinary template and either kind of map size is allowed

### Requirement: A template can state where to get it
The template catalogue SHALL allow a template to say that it comes with HotA (`built_in` is true), or to give a web link where it can be downloaded (`download`). A template states at most one of the two. A template that states neither says nothing about where to get it, and SHALL NOT be described as built in or as needing a download. A mistake in these fields SHALL stop the bot from starting, with a message that names the entry.

#### Scenario: Built into HotA
- **WHEN** a template states `built_in` as true
- **THEN** the catalogue is accepted and the template is known to come with HotA

#### Scenario: A download link
- **WHEN** a template states `download` with a link that starts with `https://`
- **THEN** the catalogue is accepted and the template is known to need a download from that link

#### Scenario: Nothing stated
- **WHEN** a template states neither `built_in` nor `download`
- **THEN** the catalogue is accepted and where to get the template is unknown

#### Scenario: Both stated
- **WHEN** a template states `built_in` as true and also a `download` link
- **THEN** the bot does not start, and the message says to state only one of the two

#### Scenario: Not a web link
- **WHEN** a template states `download` as `ftp://example` or as plain text
- **THEN** the bot does not start, and the message says the download must be a link starting with `https://`

#### Scenario: Built in stated as false
- **WHEN** a template states `built_in` as false
- **THEN** the bot does not start, and the message says to give a `download` link instead

### Requirement: A template can state its recommended simultaneous turns
The template catalogue SHALL allow a template to state how long simultaneous turns are recommended to last, as a date in the game's calendar written as month, week and day in digits: the last digit is the day (1 to 7), the one before it the week (1 to 4), and the digits before that the month. For example `117` is month 1, week 1, day 7, and `121` is month 1, week 2, day 1. A template that states nothing says nothing about it. A value in any other form SHALL stop the bot from starting, with a message that names the entry and explains the form.

#### Scenario: The end of the first week
- **WHEN** a template states `117`
- **THEN** the catalogue is accepted and the value means month 1, week 1, day 7

#### Scenario: The start of the second week
- **WHEN** a template states `121`
- **THEN** the catalogue is accepted and the value means month 1, week 2, day 1

#### Scenario: A later month
- **WHEN** a template states `1214`
- **THEN** the catalogue is accepted and the value means month 12, week 1, day 4

#### Scenario: A day or week out of range
- **WHEN** a template states `118` (day 8), `151` (week 5) or `017` (month 0)
- **THEN** the bot does not start, and the message says what the days, weeks and months can be

#### Scenario: Not digits
- **WHEN** a template states `week 1` or `1-1-7`
- **THEN** the bot does not start, and the message shows the form `117`

Open question: whether the day given is itself still played simultaneously (simultaneous turns end after it) or is the first day played in turns. Until confirmed, the bot says simultaneous turns "until" that date and does not say more.

### Requirement: A tournament sets a timer and chooses settings for its templates
A format file SHALL be able to state a timer, and to choose the roads, map size, computer players, simultaneous turns, additional rules and a download link for a template. A download link replaces the template being built into HotA. The timer is only ever stated in a format file, never in the template catalogue. It is a chess timer: three times written `mm:ss`, each with two digits of minutes and two digits of seconds, joined by plus signs, for example `12:00+06:00+02:00`, meaning the time each player has at the start, the time added at the beginning of each of their turns, and the time added when each fight starts. Settings can be written for the whole tournament (only the timer and the simultaneous turns), for a template in the tournament's list, and for a template in one phase's pool. The most specific one wins, setting by setting, over the template's own defaults.

#### Scenario: The template's default is used
- **WHEN** a format does not choose a map size for a template whose default map size is `L`
- **THEN** the template is played on `L` in every phase

#### Scenario: A timer for the whole tournament
- **WHEN** a format states the timer `12:00+06:00+02:00` for the tournament
- **THEN** every template in every phase has that timer

#### Scenario: A template chosen in the list
- **WHEN** a format chooses roads `fast` for JC in its list of templates
- **THEN** JC has fast roads in every phase, and the other templates keep their defaults

#### Scenario: A template in one phase
- **WHEN** a format chooses 6 computer players for Sapphire in the final's pool and states nothing else for it
- **THEN** Sapphire has 6 computer players in the final and its default in the other phases

#### Scenario: Another timer in a phase
- **WHEN** the tournament's timer is `12:00+06:00+02:00` and a template in the final's pool states `15:00+06:00+02:00`
- **THEN** that template has the longer timer in the final and the tournament's timer elsewhere

#### Scenario: A version that is not built into HotA
- **WHEN** the catalogue says a template is built into HotA, and a format gives that template in its list a download link
- **THEN** the template is not built in for that tournament, and the link is the one to download from

#### Scenario: Additional rules of a template
- **WHEN** the catalogue gives Nostalgia the additional rules "AI picked alternately, blue first", and a format gives Nostalgia in its list other additional rules
- **THEN** Nostalgia has the format's rules in every phase, and the other templates keep theirs

#### Scenario: Additional rules of a template in one phase
- **WHEN** a format gives Jebus Cross different additional rules in the pool of the groups than in its list
- **THEN** the groups have the pool's rules for it and the other phases have the list's

#### Scenario: A tournament-wide map size
- **WHEN** a format states a map size, roads or computer players for the whole tournament
- **THEN** validation fails and says these can only be chosen for a template

#### Scenario: A timer in the wrong form
- **WHEN** a format states the timer `12 minutes`, `12:00+06:00`, `12:00+6:00+02:00` or `12:75+06:00+02:00`
- **THEN** validation fails and shows the form `12:00+06:00+02:00` (two digits everywhere, seconds below 60)

### Requirement: What a tournament chooses must be allowed by the template
A tournament SHALL be able to choose roads, map size and computer players for a template only from the values the template allows. A template that states no allowed values for one of them cannot have it chosen. The recommended simultaneous turns can be any valid date. Validation SHALL say which template and setting is wrong and list what is allowed.

#### Scenario: An allowed choice
- **WHEN** a template allows the map sizes `M` and `L`, and a format chooses `L` for it
- **THEN** the format passes validation on that point

#### Scenario: A choice that is not allowed
- **WHEN** a format chooses the map size `XL` for a template that allows `M` and `L`
- **THEN** validation fails, names the template and the setting, and lists `M` and `L`

#### Scenario: A template that states nothing allowed
- **WHEN** a format chooses roads for a template whose roads are not stated
- **THEN** validation fails and says the template states no allowed roads, so they cannot be chosen

#### Scenario: Any date for simultaneous turns
- **WHEN** a format chooses the simultaneous turns `121` for a template that recommends `117`
- **THEN** the format passes validation on that point

### Requirement: A template can state a description and additional rules
The template catalogue SHALL allow a template to state a description and additional rules, each as free text of at most 1000 characters. The description says what the template is; the additional rules say what players must do or may not do on it, as set by the template's maker. A template that states neither says nothing. An empty text, or one longer than the limit, SHALL stop the bot from starting, with a message that names the entry and the field.

#### Scenario: Both stated
- **WHEN** a template states a description and additional rules
- **THEN** the catalogue is accepted

#### Scenario: Neither stated
- **WHEN** a template states no description and no rules
- **THEN** the catalogue is accepted and nothing is said about either

#### Scenario: A text that is too long
- **WHEN** a template states additional rules of 1001 characters
- **THEN** the bot does not start, and the message names the template and says the limit is 1000 characters

#### Scenario: An empty text
- **WHEN** a template states a description that is empty or only spaces
- **THEN** the bot does not start, and the message says to leave the field out or give a text

### Requirement: A tournament can state a description and additional rules
A format file SHALL allow the tournament to state a description and additional rules of its own, each as free text of at most 1000 characters, with the same checks as for a template. The tournament's additional rules are about the tournament as a whole; the additional rules for one template are written for that template, as settings.

#### Scenario: A tournament with additional rules
- **WHEN** a format states the additional rules "Players may agree on the length of simultaneous turns"
- **THEN** the format is accepted and the rules are known for that tournament

#### Scenario: A text that is too long
- **WHEN** a format states a description of 1001 characters
- **THEN** validation fails and says the limit is 1000 characters
