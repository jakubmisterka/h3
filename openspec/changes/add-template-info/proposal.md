# Proposal

## Why

Players still go outside Discord to find the facts about the game they are about to play: how long the clock is, whether the template comes with the game or has to be downloaded, what roads and map size it has, whether computer players are on the map, and how long simultaneous turns should last. These facts are part of the lobby ritual this bot exists to remove. Some belong to the template, and some are chosen by the tournament, so both the template catalogue and the tournament formats need to hold them.

## What Changes

### What a player sees

1. `/info <mode> <template>` also tells what is played on that template in that mode, in short lines: where to get it ("Built into HotA", or "Download: <link>"), the timer ("Timer: 12:00+06:00+02:00"), roads ("Roads: slow+mid"), map size ("Map: L+U"), computer players ("AI players: 3"), the recommended length of simultaneous turns ("Sim turns until 117"), and "Mirror: both players get the same town" for a mirror template.
2. When a match starts with a named template, the rules messages in the thread include the same lines.
3. When a pick, or the last ban for the decider's game, settles which template a game is played on, the message that announces the game gives the lines too.
4. The lobby settings that close each trade include the timer, map size, roads and computer players, so players read them off together with the towns, colors and gold.
5. Anything not stated is left out. The bot never guesses a fact.
6. A tournament and a template can also carry a short description and additional rules, as free text: for example the end turn of Jebus Cross, or how the computer players of Nostalgia are picked. `/info` shows them, and when the trade of a game starts the thread shows the additional rules of its template.

### Facts of a template (`data/templates.json`)

Besides its id, name and difficulty, a template may state:

- **Roads**, **map size** and **computer players**: each as a default and a list of allowed values. When a tournament does not say otherwise, the default is what is played.
  - Roads: `none`, or one or more of `slow`, `mid`, `fast` joined by `+` (the game's dirt, gravel and cobblestone roads). `mid` and `slow+mid` and `none` are all valid; players rarely use more than one road type, but the lobby allows it.
  - Map size: `S`, `M`, `L`, `XL`, `H`, `XH` or `G`, with `+U` when played with underground, for example `L+U`.
  - Computer players: a number from 0 to 6 (a game has at most 8 players, two of them the humans).
- **Recommended simultaneous turns**: the last day of simultaneous turns in the game's calendar, written month, week, day: `117` is month 1, week 1, day 7, and `121` is month 1, week 2, day 1. A tournament may choose another value.
- **Mirror**: `mirror: true` means both players play the same town. A mirror template is always played with underground, so all of its map sizes have `+U`.
- **Where to get it**: `built_in: true`, or `download` with a web link. At most one of them.

### Settings of a tournament (the format file)

- The **timer** is only ever set by a tournament, never by the catalogue. It is a chess timer written `12:00+06:00+02:00` (always `mm:ss`, zero-padded): 12 minutes for each player at the start, 6 minutes added at the beginning of each of their turns, and 2 minutes added each time a fight starts.
- A tournament can also choose roads, map size, computer players and simultaneous turns for a template. The choice must be one of the values the template allows; sim turns can be any valid date.
- Settings can be written for the whole tournament (only timer and sim turns, which make sense for every template), for a template in the tournament's list, and for a template in one phase's pool, with the most specific winning, as roll rules already do.

- **Description and additional rules** (`description`, `additional_rules`): free text of at most 1000 characters each. A template can state both in the catalogue; a tournament can state both in its format file. The additional rules of a template are inherited like its settings: the template's own, then replaced by the tournament's for that template, then by a phase's.

A mistake in the catalogue or in a format file is reported at start-up and by the tests, in plain words, with the file and the entry it is in.

### Assumptions

- A value that a template states no allowed list for cannot be overridden by a tournament (there is nothing to check it against); the template's facts must be completed first.
- "Built into HotA" is only said when the catalogue says so. A template with nothing stated is not described as built in, so an unknown fact is never presented as a known one.
- Every message writes the timer in its compact form only, the way it is typed into the lobby; what the three parts mean is explained once, in `data/README.md`.
- The lobby settings carry the settings that are typed into the lobby (timer, map size, roads, computer players), not the recommended simultaneous turns, which is guidance.

## Out of scope

- The real facts of the shipped templates and the real timers of tournaments. They are not invented here; the maintainers fill them in (a task for them, with the fields ready).
- Checking or enforcing any of the additional rules; they are text for players to read.
- Anything that runs or enforces a clock (timers, reminders to slow players).
- The trades that mirror and Sapphire templates need (one town drawn for both players, roulette, the sets of computer-player towns), which are separate changes. This change records that a template is a mirror and how many computer players it has.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-formats`: the template catalogue states facts with defaults and allowed values; a format file sets a timer and chooses settings with the existing most-specific-wins stacking (added requirements).
- `mode-info`: the template reply gives what is played on the template in that mode.
- `match-setup`: the thread states those facts whenever it announces the template of a game.
- `game-trade`: the lobby settings include the timer, map size, roads and computer players.

## Impact

- `data/templates.json` and its loading (`src/rules/catalogue.py`): optional fields, defaults with allowed lists, and their checks; small modules for the timer, the game date, road settings and map sizes.
- `formats/schema.json`, `src/rules/formats.py`: a `settings` object in three places, checked against the template's allowed values, and a function giving the settings of a template in a phase (as `effective_roll_rules` does for roll rules).
- The text of `/info` for a template, the rules messages at the start of a match, the message that announces a decided game, and the lobby settings (plain functions in `src/rules/`).
- `data/README.md` and `formats/README.md` (the fields, with examples) and tests for each rule above. No new dependency.
