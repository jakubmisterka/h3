## Context

Today `Trade` (`src/rules/trade.py`) is one shape: `first_pair`, a list of `rolls`, and two `reports` (`town_bid`, `color_bid`). The sections are hard-coded (`REPORTED_SECTIONS`, the `town_roll` section), the records that carry the trade (`tr`, `rl`, `rs`, `tb`, `cb` in `src/state.py`) are read back from the text of the bot's messages (mentions and `` `quoted` `` words), and a trade's pair is "the first two quoted words". The command `/trade report` takes a town or a color. The spec already says "Trade sections come from data", but nothing implements it.

The three new kinds differ from the standard trade in what is drawn, what a roll redraws, and which bids follow. Mirror and roulette are independent (a roulette can be traded on a mirror template or not), and which kind a template gets can change between phases of one tournament.

## Goals / Non-Goals

**Goals:** a trade kind chosen by data and stacked like the other settings; the standard trade stays exactly as it is (the existing tests are the safety net); mirror, computer-player packs and roulette (both mirror and not, with hero bans and `roll_before_heroes`); every new step is a record, so status, autocomplete and undo keep working.

**Non-Goals:** tracking which hero or color players finally take; running any hero procedure the bot does not draw; the 200% color toss; filling the hero catalogue with the whole game (the maintainers extend it).

## Decisions

### 1. The kind is a setting; mirror stays a fact

`trade` joins the template settings of `template_settings.py` (catalogue default, then the tournament's list entry, then the phase's pool entry, as `additional_rules` and `sim_turns` do). It is written as a string (`"standard"`, `"standard_with_ai_packs"`) or an object `{ "kind": "roulette", "hero_bans": 1, "roll_before_heroes": true }`. A small module `rules/trade_kinds.py` reads it into a frozen `TradeKind(name, hero_bans, roll_before_heroes)` (the same reader for the catalogue and the format file) and says, for a kind and a mirror flag, the **sections** of the trade. `Settings` gets a `trade: TradeKind` (default standard). `mirror` stays what it is: a fact of the template, not part of the kind, so roulette combines with it freely.

The tournament-wide `settings` refuses `trade` with an explanation, like `roads`.

### 2. Sections are data

`sections(kind, mirror)` returns the ordered tuple of sections, where a section is a name:

| Kind | Sections (after the draw) |
|---|---|
| standard | `town_roll`, `town_bid`, `color_bid` |
| standard, mirror | `town_roll`, `color_bid` |
| `standard_with_ai_packs` | `town_roll`, `town_bid`, `pack_bid`, `color_bid` |
| roulette | `town_roll`, `hero_bans` (only when `hero_bans > 0` and `roll_before_heroes`), then `town_bid`, `color_bid` |
| roulette, mirror | `town_roll`, `hero_bans` (as above), `first_choice_bid` |

The sections are typed (`Section(name, bid, choice_field)` in `SECTION_TABLE` of `trade_kinds.py`), so a bid and the record field that holds its choice come from one table, not from the section's name. `Trade.section` (the one expected next) is worked out from this tuple and what is recorded, instead of from `REPORTED_SECTIONS`. `town_roll` still ends when nobody can or wants to roll, and reporting the first bid still counts as skipping the rolls still open, except in a roulette: its bid is refused until the heroes are drawn, so its roll section has to end by rolling or skipping.

The existing wording, replay and prompts are moved behind this table by a first, behavior-preserving step (milestone A starts with it): all current tests stay unchanged and green before any new kind is added.

### 3. The draw is a value that the kind knows the shape of

A trade starts with a `Draw`: the towns (1 for a mirror, otherwise 2), for packs also `pack1` and `pack2` (3 towns each), and for roulette with `roll_before_heroes: false` also the heroes. The record `tr` carries them as its `` `quoted` `` words, in this order, and `rl` carries the banned towns first and then the new draw. Since the reader of a record does not know the trade's kind, `state.py` reads all the quoted words (`words`) and `rules/trade.py` splits them, because it knows the draw's size (1, 2, 8, or 2 plus the heroes). A record with exactly two words is a standard draw, as before, so existing threads are read as they were.

The draws live in `rules/trade_draw.py` with the `Draw(towns, packs)` value (heroes are added in milestone B) and `draw_shape(kind, mirror)`, the one table of how many towns a kind draws, which the draws, the replay checks and the reading of records all use. The thread quotes a town by its name, not its id (`Castle`, not `Castle (`castle`)`); the names of towns are single capitalised words (a test of the shipped data keeps it so). `replay_trades` maps each quoted name back to its id with the town catalogue, and still reads older threads that quote ids. The wording module builds the data of the records it writes (`start_data`, `roll_data`, `report_data`), so which words are quoted is decided in one place. Draws are plain functions with an injected `random.Random`, tested for fairness and distinctness as `draw_pair` is: `draw_pair` (unchanged), `draw_town`, `draw_with_packs` (the pair from the unbanned towns, then six packs towns from the others), `draw_heroes` (mirror: 2 distinct heroes of the town; otherwise 1 per town of the pair; never a banned hero or one in the template's `banned_heroes`).

### 3b. A skip lasts until the towns change

`Trade.skipped` holds the players who passed on the draw that stands now; every roll clears it (`with_roll`). So a skip is "not these towns", not "no more rolls": when the other player rolls, the one who skipped can roll again (rolls left and gold permitting) or skip again. The roll section ends when nobody is left to roll, as before: each player has used their rolls, cannot pay, or has skipped since the towns last changed. Replay needs no new record: a `roll_skipped` record counts only until the next `roll` record.

### 4. Mirror: a roll bans the standing town

A mirror's roll names no town: the roll bans the town that stands, pays the roll cost and draws another allowed, unbanned town. The record stores that ban (so replay stays a pure check of what is recorded). The roll rules are unchanged (cost, rolls per player); `max_roll_bans` does not apply, since there is nothing to choose.

### 5. Packs

`standard_with_ai_packs` redraws all 8 on a roll, and only towns of the player pair can be banned. A banned town is banned for the players only: the new pair is drawn from the allowed towns that are not banned, and the packs from the other allowed towns, so a banned town may come up in a pack (decided with the maintainers). The `pack_bid` is reported as `pack1` or `pack2`; the other player gets the other pack. The message announcing the draw lists the pair and the two packs; the packs go into the quoted words of the record.

### 6. Roulette steps are records the bot makes or players report

- `heroes_banned` (code `hb`): a player and the hero ids they ban (possibly none). Players ban in turn, the coinflip winner (A) first. The command is `/trade ban-heroes` with up to three optional hero options (and no option means "no ban"); the number allowed is `hero_bans`.
- `heroes_drawn` (code `hd`): the drawn hero ids. The bot posts it, like a skipped roll it posts before a bid: the handler of the step that completes the previous step (the last roll or skip of the roll section when there are no bans, the second player's hero ban otherwise, and the opening of a trade where nobody can roll) calls one function, `automatic_steps`, which says whether the draw is due, and posts the record.
- A mirror roulette's bid is `first_choice_bid` (code `fb`), with the winner, the amount and `hero` or `color`. A non-mirror roulette reuses `town_bid` (the hero follows the town) and `color_bid`.
- Replay checks each hero of a `heroes_drawn` record: right town, not banned by a player, not in the template's `banned_heroes`, and the right count. It cannot check randomness, as it cannot for towns.

`roll_before_heroes: false` puts the heroes into the draw of `tr` and of every `rl`; there is no `hero_bans` step then.

### 7. Hero data

`data/heroes.json` is a catalogue like the town and template ones (id, name, plus `town` and `link`), parsed by the same `parse_catalogue` with two required fields and a check that the town exists and the link is `https://`. The registry loads it between the towns and the templates; a template's optional `banned_heroes` is checked against it. `Registry` gets `heroes`, defaulting to an empty catalogue, so tests and code that do not need heroes are untouched.

Format validation gets the hero catalogue as an optional argument (`validate_format(data, templates, towns, heroes=None)`) for the checks that need it: a roulette needs heroes, and every allowed town must keep enough heroes after the template's banned heroes and the bans players could make.

### 8. Discord layer

`/trade report` keeps its three options; the `choice` option is checked against the section that is expected (a town, `pack1`/`pack2`, `hero`/`color`, `red`/`blue`) and its autocomplete offers the right set for it. One new command, `/trade ban-heroes`, with autocomplete over the heroes of the drawn town(s). Handlers stay thin: all checks and wording are in `rules/`, in the marked wording blocks.

### 9. Undo, status and next steps

`next_steps` already decides what to say from the latest counting step; it learns the new sections through `Trade.section`. `/match status` lists the section that is next. Undo treats the new records like the others, with one exception: a `heroes_drawn` record is made by the bot together with the step before it, so undo cannot start at it (a message tells the players to undo from the step before). Undoing the step before the draw rewinds the draw as well, and the bot draws again after it.

### 10. The mirror hero procedure is text

Banning and choosing the starting hero in a mirror-standard trade (who bans how many, who picks first) is not run by the bot. A format states it in its `additional_rules`, and `formats/README.md` shows an example.

## Alternatives considered

- **One enum for kinds with mirror among them** (`mirror`, `mirror_roulette`, ...): rejected, because mirror and roulette combine and the combinations would multiply.
- **A kind per template only:** rejected, because the tournament this is built for trades the same templates as a plain mirror in the groups and as a roulette in the knockout.
- **Storing the sections in the data files:** rejected for now: there are four shapes and each comes with its own rules and wording, so code that reads a table is simpler to test than a configuration language.
- **A separate `/trade` command per bid:** rejected; `/trade report` already means "report the result of the bid that is next".

## Risks / Trade-offs

- **The refactor of `Trade` is the biggest risk.** The first step (sections as a table) changes no behavior and is protected by the existing tests, and each new kind is added behind it. Replay still raises with the message number when a thread does not fit.
- **Quoted-word records are fragile:** more words per record (up to 8 towns). Mitigated by one reader per record that returns the words, one place that splits them, and tests that parse what the wording functions produce.
- **Message length:** the packs announcement lists 8 towns and the roulette one lists heroes; the wording is kept short and tested against Discord's 2000-character limit with the longest names.
- **Autocomplete within 3 seconds:** the choice and hero autocompletes use the existing cached read of the thread.
- **Hero data is large and partly unknown to us:** the hero catalogue and the per-template `banned_heroes` are data for maintainers; the bot refuses to start on mistakes, and the format check names the town that has too few heroes.

## Open Questions

- Whether a banned town also leaves the computer-player packs (provisionally yes).
- The tournament's exact procedure for choosing the hero in a mirror-standard trade differs between tournaments, so it stays text.
- The heroes' wiki links and each template's excluded heroes are data to be collected by the maintainers.
