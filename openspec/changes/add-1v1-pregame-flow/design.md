# Design

## Context

The repo has `src/bot.py` (a `discord.Client` with one `/hello` command, guild sync in dev and global sync in prod) and `src/config.py`. There is no test setup yet, and no storage. See proposal.md for the flow and for what is out of scope; the specs hold the requirements.

Constraints from the project: slash commands only, no privileged intents, async code that never blocks the loop, Discord handlers kept thin, rule logic in plain functions with pytest tests.

## Goals / Non-Goals

**Goals:**
- All rules (selection sequence, ledger, validation) are plain, synchronous, unit-tested functions with no Discord imports.
- A contributor can add a format with a JSON file and nothing else.
- The bot holds no data between events: any command can be served after a restart.

**Non-Goals:**
- No database, cache or background jobs.
- No interactive components. Buttons and modals can be added later without changing the rules layer.

## Decisions

### 1. Layers: rules, state, Discord

```
 src/bot.py            discord.Client, registers commands
 src/discord_commands/*.py thin Discord handlers: check channel, call state + rules, post reply
 src/state.py          rebuild a Match from thread messages  (Discord objects in, plain data out)
 src/rules/*.py        selection, ledger, validation          (pure functions, no discord import)
 data/towns.json      the town catalogue
 data/templates.json   the template catalogue
 formats/*.json        rule-sets
 formats/schema.json   JSON Schema for them
```

A handler loads the match from the thread, calls a rules function with the match and the player's input, gets back either an error message or the new event, posts the event, and replies. Rules functions never see Discord objects, so every scenario in the specs can be a pytest case.

*Alternative:* put logic in the command handlers. Rejected: untestable without Discord, and the project asks for the opposite.

### 2. Match state is an append-only event log in the bot's own messages

Every accepted action (match started, coinflip, ban, pick, roll, town bid, color bid, undo) is posted by the bot as one message that starts with a tag, `[#<number> <code>]`, followed by the text players read, for example `[#3 ban] <@111> banned JC`. The number counts the records, so a deleted message shows as a gap; the code says which kind of record it is; and the data (players, templates, amounts) is read out of the text in a fixed order, from the start, by rules that depend on the code, so wording around the data is free. To serve a command, the bot fetches the thread history, keeps its own messages, parses the records, and folds them into the current match. Undo is itself an event that cancels the previous trade event, so the history stays honest.

```
 events:  MatchStarted -> CoinFlip -> Ban -> Ban -> Pick -> ... -> TradeReport -> Undo -> TradeReport
 fold  :  events -> Match { phase, A, B, pool, games[], trade per game, gold }
```

Reading the bot's own messages does not need the Message Content intent. The bot needs Read Message History in threads.

*Alternatives:* (a) SQLite or Postgres: more to run and back up, explicitly deferred by the maintainer. (b) Parse players' free text: needs the privileged intent, rejected. (c) In-memory state: lost on restart, and players are slow, so restarts will happen mid-match.

### 3. Formats: one JSON file per mode, validated by schema plus rules

```
 { "id": "...", "name": "...", "status": "active|archived", "thread_visibility": "public|private",
   "roll_rules": { "roll_cost", "rolls_per_player", "max_roll_bans" },        (optional, every template)
   "allowed_towns": [ "<town id>", ... ],                                      (optional, every phase; default: all)
   "templates": [ "<template id>" | { "template": "<id>", "roll_rules": {...} }, ... ],
   "phases": [ { "name", "best_of",
                 "pool": [ "<template id>" | { "template": "<id>", "roll_rules": {...} }, ... ],  (optional: all)
                 "template_selection": { "type": "sequence",
                                "steps": [{"who":"A","do":"ban"}, ..., {"do":"decider"}] }
                          or { "type": "agreed" },
                 "allowed_towns": [ "<town id>", ... ] } ] }                   (optional, replaces the tournament's)
```

The template catalogue is `data/templates.json`: a list of `{ "id", "name", "difficulty" }` entries, starting with `JC`, `6lm10a` and `h3dm1`. Difficulty is a property of the template, because that is how the template is played; a format does not state it, and starting gold follows from it. The town catalogue has only `id` and `name`. The loader takes the extra fields a catalogue requires, so a template can grow more fields later (a timer, a download link).

Example, the small development format `formats/el-classico.json` (real tournaments will replace it):

```
{ "id": "el-classico", "name": "El Classico", "status": "active",
  "templates": ["JC", "6lm10a", "h3dm1"],
  "phases": [ { "name": "Main", "best_of": 1,
                "template_selection": { "type": "sequence",
                               "steps": [ {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"},
                                          {"do": "decider"} ] } } ] }
```

No `roll_rules` and no `pool` are written, so the defaults (500 gold, 1 roll each, 0 to 2 bans) apply and the phase uses all three templates; `allowed_towns` is left out, so all 12 towns are allowed.

Allowed towns follow the same idea as the templates: a tournament may write `"allowed_towns": ["castle", ...]` for all its phases, a phase may write its own list, which replaces the tournament's for that phase, and when neither is written every town in the catalogue is allowed. The list is resolved once, when the format is loaded.

The town catalogue is `data/towns.json`: a list of `{ "id", "name" }` entries, starting with the 12 towns on the community wiki (original game: Castle, Rampart, Tower, Inferno, Necropolis, Dungeon, Stronghold, Fortress; Armageddon's Blade: Conflux; Horn of the Abyss: Cove, Factory, Bulwark). Formats and the trade commands refer to towns by `id`; the catalogue is loaded once at start-up and validated like a format (unique ids, non-empty names), and the command autocomplete is built from it.

Starting gold is not in any file. A small table in the rules layer maps a template's difficulty to the game's human-player gold (80% to 30000, 100% to 20000, 130% to 15000, 160% to 10000, 200% to 0; values from the community wiki). A template with a difficulty outside the table is refused when the catalogue is loaded. The default section list is also chosen by the template's difficulty: 200% replaces all three sections with a single `color_toss` section (the lobby is all-random there, so there is nothing else to trade), whose coin is flipped with the same injectable random source as the coinflip.

`formats/schema.json` checks the shape. A Python validator checks what a schema cannot: pool size = number of steps (each template is banned, picked or taken by the decider), the decider is last, and picks plus decider make as many games as the best-of. The games are played in the order of the picks, then the decider, so no separate game order is stored. A pytest test loads every file in `formats/`, so a bad contributor file fails CI. The effective roll rules of a template in a phase are the built-in defaults, updated by the tournament's `roll_rules`, then by the template's entry in the tournament list, then by its entry in the phase's pool, in one function. The tournament lists its templates once and each phase selects from them, so the bot can answer "which templates are in this tournament?" and a template's settings are written in one place; a timer, when added, is one more setting group that works the same way.

*Alternative:* YAML or Python files. Rejected: the project already says JSON, and JSON can be validated without running contributor code.

### 4. Slash commands

| Command | Used where | Purpose |
|---|---|---|
| `/info mode [template]` | any channel | shows a mode, or one template in a mode; reply only the asker sees |
| `/match start mode opponent [phase] [template]` | any channel | creates the thread there, coinflip |
| `/ban template`, `/pick template` | match thread | selection step, autocomplete from remaining pool |
| `/trade roll [ban_1] [ban_2]`, `/trade skip-roll` | match thread | roll the town pair (bot draws the new pair), or skip the remaining rolls (only the roll, not the trade) |
| `/trade start [game]` | match thread | opens the trade of a game, named by its number or its template (without a name: the first known game whose trade is not finished); closes the open trade as incomplete |
| `/trade report ...` | match thread | reports a bid result of the open trade's current section |
| `/trade undo` | match thread | cancels the latest trade report |
| `/match status` | match thread | the records, the next selection step, and every started trade with its section and gold |

`phase` is shown only when the chosen mode has several phases; because a slash command's options cannot appear conditionally, the option is optional and the bot answers with a follow-up prompt asking for it when it is missing and needed. The fields of `/trade report` depend on the section (roll, town, color), so they are optional and checked by the rules function. The exact set of fields is settled when the first version is tried in the dev guild.

*Alternative:* one command per section (`/roll`, `/town`, `/color`). Cleaner fields, more commands to learn. Revisit after first use.

### 4a. The bot's random draws are events

The town pair, each reroll and the 200% toss are drawn by the bot, so they cannot be recomputed after a restart. Each draw is posted as its own event (for example `PairDrawn` with the two town ids, `ColorTossed` with the winner) and the fold reads the result from the event instead of drawing again. Draws come from one function, `draw_pair(allowed, banned, rng)`, which takes an injectable random source so tests can fix it; it uses the system's secure random generator in production. Because draws are final, undo skips them: undo removes only the latest player report, and refuses when that is a roll or a toss.

*Alternative:* derive draws from a seed stored in the thread, so they could be recomputed. Rejected: the event already holds the answer, and a seed in a public thread would let anyone predict future pairs.

### 4b. The info command reads only the loaded formats

`/info` needs no match, no thread and no events: it looks the mode up in the formats loaded at start-up and builds a text. The text is built by plain functions (`info_for_mode(format)`, `info_for_template(format, template)`) that return a string, so every scenario in the `mode-info` spec is a pytest case, and the handler only finds the format, calls the function and sends the result as an ephemeral reply. Template info uses the same effective-settings function as the trade (phase defaults updated by the template's overrides), so what `/info` says is what a match will do. Because it shows the result of the validated format file, it doubles as a quick way for contributors to check a new file.

The template catalogue stays `{ "id", "name" }` for now. Timers and download links are a follow-up; they would be optional fields there.

### 5. Gold as whole numbers

Gold is stored as integers; a payment moves an amount from one player to the other, so the total stays constant. The ledger function takes the template's difficulty (for the starting gold), the roll rules and the list of trade events and returns both players' gold, so undo is "drop the last event and recompute".

### 6. Concurrency

Two commands can arrive in one thread at nearly the same time. Per thread, handlers run under an in-process lock (a dict of `asyncio.Lock` keyed by thread id), and each handler rebuilds the match after taking the lock. The bot runs as one process, so this is enough.

### 7. Trades: one open at a time, the game in the tag

A game's trade can start as soon as its template is known: the k-th game is known when the k-th pick is made, and the decider's game once selection has ended. So a trade can start while selection goes on, and its records interleave with the bans and picks in the same thread. Everything stays in one numbered sequence (a deleted message is detected anywhere), and the records that belong to a game carry its number in the tag, for example `[#7 tr g1]` (trade of game 1 started) and `[#8 tb g1]` (its town bid). The plain messages of a trade start with "Game 1:", so players can see which trade they are in.

Only one trade is open at a time. Starting a trade (`/trade start`, naming the game or its template) closes the open one: it keeps its records and counts as incomplete. Starting it again reopens it where it stopped, with the same pair and gold, because random results are final. The records say which trade is open: the latest trade start or reopening. Reporting, rolling, skipping the roll and undoing act on the open trade only, so those commands need no game option. A finished trade cannot be started again.

After an action the bot announces the next step of that action's own context only (the next ban, or the next section of the open trade). `/match status` is the one place that lists everything open: the next selection step and every started trade with its section and gold.

*Alternative:* several trades open at once, each command naming its game. Rejected by the maintainer: players who start a second trade have almost certainly finished the first elsewhere, and two open trades only invite reports to the wrong game.

## Risks / Trade-offs

- **[A bot message needed for the state is deleted or edited]** → The bot refuses to guess and says the match cannot be rebuilt. Bot messages are the bot's own, so only moderators can delete them; the thread is the audit trail.
- **[Reading a long thread on every command is slow]** → A match has at most a few dozen bot events, so one history fetch is small. If it ever matters, cache the folded match in memory per thread, keeping the thread as source of truth.
- **[Archived threads may behave unexpectedly with slash commands]** → Not tested. Threads are created with the longest auto-archive time (7 days of silence), which is assumed to be enough. If players do hit archived threads and commands fail there, they reopen the thread by hand; automatic resume is left to the rewind follow-up (see proposal.md).
- **[The bot cannot verify what players report]** → Accepted by design (either player reports, no confirmation). Undo and the visible thread are the safeguards; a moderator-resolve command is a later option.
- **[Rules are unclear in places]** → Recorded as "Open question:" in the specs. Rules code takes the provisional default in one place each, so changing one is a small edit.
- **[Command fields are guessed before real use]** → Keep `/trade report` fields flexible and tune in the dev guild before the prod sync.

## Open Questions

- Whether to also expose `/trade report` per section as separate commands, decided after trying it.
- Naming of "mode" vs "format" in user-facing text.
