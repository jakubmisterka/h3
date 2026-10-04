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
 src/commands/*.py     thin handlers: check channel, call state + rules, post reply
 src/state.py          rebuild a Match from thread messages  (Discord objects in, plain data out)
 src/rules/*.py        selection, ledger, validation          (pure functions, no discord import)
 data/factions.json    the faction (town) catalogue
 data/templates.json   the template catalogue
 formats/*.json        rule-sets
 formats/schema.json   JSON Schema for them
```

A handler loads the match from the thread, calls a rules function with the match and the player's input, gets back either an error message or the new event, posts the event, and replies. Rules functions never see Discord objects, so every scenario in the specs can be a pytest case.

*Alternative:* put logic in the command handlers. Rejected: untestable without Discord, and the project asks for the opposite.

### 2. Match state is an append-only event log in the bot's own messages

Every accepted action (match started, coinflip, ban, pick, roll, faction bid, color bid, undo) is posted by the bot as one message: a readable line for players plus a compact machine part (an embed footer holding a small JSON event). To serve a command, the bot fetches the thread history, keeps its own messages, parses the events, and folds them into the current match. Undo is itself an event that cancels the previous trade event, so the history stays honest.

```
 events:  MatchStarted -> CoinFlip -> Ban -> Ban -> Pick -> ... -> TradeReport -> Undo -> TradeReport
 fold  :  events -> Match { phase, A, B, pool, games[], trade per game, gold }
```

Reading the bot's own messages does not need the Message Content intent. The bot needs Read Message History in threads.

*Alternatives:* (a) SQLite or Postgres: more to run and back up, explicitly deferred by the maintainer. (b) Parse players' free text: needs the privileged intent, rejected. (c) In-memory state: lost on restart, and players are slow, so restarts will happen mid-match.

### 3. Formats: one JSON file per mode, validated by schema plus rules

```
 { "id": "...", "name": "...", "status": "active|archived", "thread_visibility": "public|private",
   "phases": [ { "name", "best_of", "pool": [template ids],
                 "selection": { "type": "sequence", "steps": [{"who":"A","do":"ban"}, ...],
                                "game_order": ["A_pick","B_pick","decider"] }
                          or { "type": "agreed" },
                 "trade": { "difficulty", "roll_cost", "rolls_per_player", "max_roll_bans",
                            "sections": [...] },
                 "template_overrides": { "<template id>": { "difficulty": ... } } } ] }
```

The template catalogue is `data/templates.json`, the same shape as the faction one: a list of `{ "id", "name" }` entries, starting with `JC`, `6lm10a` and `h3dm1`. Difficulty is not a property of the template; it is a phase default (and an optional per-template override in the phase), because all three first templates share 160%.

Example, the first format `formats/el-classico.json`:

```
{ "id": "el-classico", "name": "El Classico", "status": "active",
  "phases": [ { "name": "Main", "best_of": 1,
                "pool": ["JC", "6lm10a", "h3dm1"],
                "selection": { "type": "sequence",
                               "steps": [ {"who": "A", "do": "ban"}, {"who": "B", "do": "ban"} ],
                               "game_order": ["decider"] },
                "trade": { "difficulty": 160 } } ] }
```

Roll values are left out, so the defaults (500 gold, 1 roll each, 0 to 2 bans) apply; `allowed_factions` is left out, so all 12 towns are allowed.

A phase may add `"allowed_factions": ["castle", ...]`; when absent, every faction in the catalogue is allowed.

The faction catalogue is `data/factions.json`: a list of `{ "id", "name" }` entries, starting with the 12 towns on the community wiki (original game: Castle, Rampart, Tower, Inferno, Necropolis, Dungeon, Stronghold, Fortress; Armageddon's Blade: Conflux; Horn of the Abyss: Cove, Factory, Bulwark). Formats and the trade commands refer to factions by `id`; the catalogue is loaded once at start-up and validated like a format (unique ids, non-empty names), and the command autocomplete is built from it.

Starting gold is not in the file. A small table in the rules layer maps difficulty to the game's human-player gold (80% to 30000, 100% to 20000, 130% to 15000, 160% to 10000, 200% to 0; values from the community wiki). A difficulty outside the table fails validation. The default section list is also chosen by difficulty: 200% replaces all three sections with a single `color_toss` section (the lobby is all-random there, so there is nothing else to trade), whose coin is flipped with the same injectable random source as the coinflip.

`formats/schema.json` checks the shape. A Python validator checks what a schema cannot: pool size = steps + 1, picks = best_of - 1, game order covers every game once. A pytest test loads every file in `formats/`, so a bad contributor file fails CI. The effective trade settings of a template are the phase defaults updated by the template's overrides, in one function.

*Alternative:* YAML or Python files. Rejected: the project already says JSON, and JSON can be validated without running contributor code.

### 4. Slash commands

| Command | Used where | Purpose |
|---|---|---|
| `/match start mode opponent [phase] [template]` | any channel | creates the thread there, coinflip |
| `/ban template`, `/pick template` | match thread | selection step, autocomplete from remaining pool |
| `/trade roll [bans]`, `/trade decline` | match thread | roll the faction pair (bot draws the new pair), or skip the roll |
| `/trade report ...` | match thread | reports a bid result of the current trade section |
| `/trade undo` | match thread | cancels the latest trade report |
| `/trade status` | match thread | shows section, gold, what is expected |

`phase` is shown only when the chosen mode has several phases; because a slash command's options cannot appear conditionally, the option is optional and the bot answers with a follow-up prompt asking for it when it is missing and needed. The fields of `/trade report` depend on the section (roll, faction, color), so they are optional and checked by the rules function. The exact set of fields is settled when the first version is tried in the dev guild.

*Alternative:* one command per section (`/roll`, `/faction`, `/color`). Cleaner fields, more commands to learn. Revisit after first use.

### 4a. The bot's random draws are events

The faction pair, each reroll and the 200% toss are drawn by the bot, so they cannot be recomputed after a restart. Each draw is posted as its own event (for example `PairDrawn` with the two faction ids, `ColorTossed` with the winner) and the fold reads the result from the event instead of drawing again. Draws come from one function, `draw_pair(allowed, banned, rng)`, which takes an injectable random source so tests can fix it; it uses the system's secure random generator in production. Because draws are final, undo skips them: undo removes only the latest player report, and refuses when that is a roll or a toss.

*Alternative:* derive draws from a seed stored in the thread, so they could be recomputed. Rejected: the event already holds the answer, and a seed in a public thread would let anyone predict future pairs.

### 5. Gold as whole numbers

Gold is stored as integers; a payment moves an amount from one player to the other, so the total stays constant. The ledger function takes the effective trade settings and the list of trade events and returns both players' gold, so undo is "drop the last event and recompute".

### 6. Concurrency

Two commands can arrive in one thread at nearly the same time. Per thread, handlers run under an in-process lock (a dict of `asyncio.Lock` keyed by thread id), and each handler rebuilds the match after taking the lock. The bot runs as one process, so this is enough.

## Risks / Trade-offs

- **[A bot message needed for the state is deleted or edited]** → The bot refuses to guess and says the match cannot be rebuilt. Bot messages are the bot's own, so only moderators can delete them; the thread is the audit trail.
- **[Reading a long thread on every command is slow]** → A match has at most a few dozen bot events, so one history fetch is small. If it ever matters, cache the folded match in memory per thread, keeping the thread as source of truth.
- **[Archived threads may behave unexpectedly with slash commands]** → Test on the dev bot early (first task after the skeleton). If commands fail in archived threads, players reopen the thread by hand; automatic resume is left to the rewind follow-up (see proposal.md).
- **[The bot cannot verify what players report]** → Accepted by design (either player reports, no confirmation). Undo and the visible thread are the safeguards; a moderator-resolve command is a later option.
- **[Rules are unclear in places]** → Recorded as "Open question:" in the specs. Rules code takes the provisional default in one place each, so changing one is a small edit.
- **[Command fields are guessed before real use]** → Keep `/trade report` fields flexible and tune in the dev guild before the prod sync.

## Open Questions

- Whether to also expose `/trade report` per section as separate commands, decided after trying it.
- Naming of "mode" vs "format" in user-facing text.
