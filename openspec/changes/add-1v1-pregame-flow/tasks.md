# Tasks

## 1. Setup

- [ ] 1.1 Remove the `/hello` command from `src/bot.py` and fix the syntax error (`def main() ->  :` should be `-> None:`); verify `poetry run python -c "import ast; ast.parse(open('src/bot.py', encoding='utf-8').read())"` succeeds, the bot logs in on the dev app, and `/hello` no longer appears in the dev guild
- [ ] 1.2 Add `pytest` (dev group) and a JSON-schema validator with `poetry add`, commit `poetry.lock`, and verify `poetry run pytest` runs and reports no tests collected instead of an import error
- [ ] 1.3 Create the layout from the design (`src/rules/`, `src/commands/`, `formats/`, `tests/`) and verify the package imports in a pytest smoke test
- [ ] 1.4 Test in the dev guild that the bot can create threads, send in threads and read message history, and that slash commands work in an archived thread; write the result under Open questions in `design.md` and verify the spec's archived-thread open question is updated to match

## 2. Tournament formats

- [ ] 2.1 Write `formats/schema.json` for the format shape in the design and verify it accepts a hand-written example and rejects a file missing `phases`
- [ ] 2.2 Implement the format loader and rule validator (pool = steps + 1, picks = best_of - 1, game order covers each game once, unknown fields rejected) as pure functions, with pytest cases for each scenario in the `tournament-formats` spec
- [ ] 2.3 Implement effective trade settings (phase defaults updated by template overrides, with the spec's default roll values) and the difficulty-to-starting-gold table (80%, 100%, 130%, 160%, 200%) and the default section list per difficulty, with pytest cases for override, no override, default rolls, each difficulty's gold and sections, and rejection of an unknown difficulty or a starting gold written in the file
- [ ] 2.3a Add `data/factions.json` with the 12 wiki towns and implement its loader and validation (unique ids, non-empty names) plus the per-phase allowed-factions rule (default all, restricted subset, unknown faction rejected), with pytest cases for each scenario in the "Factions come from one catalogue" requirement
- [ ] 2.3b Add `data/templates.json` with JC, 6lm10a and h3dm1 and implement its loader and validation (unique ids, non-empty names) plus the pool check against it, with pytest cases for each scenario in the "Templates come from one catalogue" requirement
- [ ] 2.4 Add `formats/el-classico.json` (one phase, BO1, pool of JC / 6lm10a / h3dm1, sequence A ban, B ban, 160% difficulty, default rolls, all factions), and verify a pytest test that loads every file in `formats/` passes and that El Classico's selection leaves exactly one template, with 10000 gold per player
- [ ] 2.5 Implement the list of selectable modes (archived formats hidden, starting in an archived one refused) with pytest cases for both scenarios
- [ ] 2.6 Document how to add a format in `formats/README.md` (fields, an example, how to run the validation) and verify a newcomer can follow it by copying the ranked example and passing `poetry run pytest`

## 3. Match state in the thread

- [ ] 3.1 Define the event types and their compact machine format (small JSON in an embed footer) in `src/state.py`, with pytest round-trip tests for encode and decode
- [ ] 3.2 Implement the fold from a list of events to a `Match` (phase, A, B, pool, games, per-game trade) as a pure function, with pytest cases for a clean run, undo, an unknown event, and a missing start event (the "cannot be rebuilt" scenario)
- [ ] 3.3 Implement the Discord side: fetch thread history, keep the bot's own messages, parse events; and post an event with its readable text. Verify in the dev guild that a restarted bot continues a half-finished selection
- [ ] 3.4 Add the per-thread lock and verify with a pytest asyncio test that two simultaneous commands on one thread run one after the other

## 4. Match start and coinflip

- [ ] 4.1 Implement start validation (self or bot as opponent, phase needed or not, template required and allowed for agreed phases) as pure functions, with pytest cases for each scenario in the `match-setup` spec
- [ ] 4.2 Implement the coinflip with an injectable random source, and pytest cases for a fixed source and for each outcome being possible
- [ ] 4.3 Implement `/match start` as a thin handler: create the thread (public or private per format), mention both players, post the start and coinflip events. Verify in the dev guild for a single-phase, a multi-phase and a ranked mode
- [ ] 4.4 Reject commands from non-players and from outside a match thread, with pytest cases for both and a dev-guild check

## 5. Template selection

- [ ] 5.1 Implement the selection step function (whose turn, which action, template still available, remaining pool, ending with ordered games) as pure functions, with pytest cases for every scenario in the `template-selection` spec including the 9-template sequence and the 7-template sequence from the explore session
- [ ] 5.2 Implement `/ban` and `/pick` as thin handlers with autocomplete of the remaining pool, turn announcement, remaining-pool message and the final games announcement. Verify a full BO3 selection in the dev guild
- [ ] 5.3 Implement the agreed-template path (skip selection, go to the trade) and verify a ranked match reaches the trade directly in the dev guild

## 6. Game trade

- [ ] 6.1 Implement the gold ledger (payments to the opponent, whole numbers, balance check, undo by dropping the last event) as pure functions, with pytest cases including the worked example (10400 and 9600)
- [ ] 6.2 Implement the section state machine (roll, faction, color, in order, data-driven section list) and the report validation (bans within limit, roll allowance, factions allowed in the phase, a pair of two different factions, faction in the pair, color red or blue, amount within gold), with pytest cases for each scenario in the `game-trade` spec
- [ ] 6.2b Implement the roll section: `draw_pair(allowed, banned, rng)` (two different allowed, non-banned factions, uniform, refuses when fewer than two remain), eligibility (rolls left and enough gold), roll and decline, the implicit decline when a faction bid is reported, and refusing undo of rolls and tosses; with pytest cases (seeded random source) for each scenario in the "The bot generates the faction pair", "A roll costs gold and draws a new pair" and "Each eligible player rolls or declines" requirements, including a statistical check that every allowed faction appears
- [ ] 6.2a Implement the 200% color toss section (fair coin from an injectable source, winner chooses red or blue, no gold moves, no roll or faction steps), with pytest cases for each scenario in the "At 200% difficulty only the color is tossed" requirement
- [ ] 6.3 Implement the lobby settings summary as a pure function that builds the text from a finished trade, with a pytest case for the spec's summary scenario
- [ ] 6.4 Implement `/trade roll`, `/trade decline`, `/trade report`, `/trade undo` and `/trade status` as thin handlers, including the bot's announcement at the start of each section (for the roll: the pair, the cost and who may roll) and the gold after each change. Verify a full game trade in the dev guild
- [ ] 6.5 Make the trade of each game independent: default to the first unfinished game, allow naming a game, and verify with a pytest case and in the dev guild that game 2 can be traded after a pause while game 1 stays complete

## 7. Wrap-up

- [ ] 7.1 Update `CLAUDE.md` (it still says the bot is a single `/hello` command) for the new commands, modules and the `formats/` directory, and verify it matches `git ls-files src formats`
- [ ] 7.2 Run a complete match in the dev guild from `/match start` to the final lobby settings, including a bot restart in the middle and a reopened thread, and record any rule that needed a guess under the specs' Open question entries
- [ ] 7.3 Run the final `poetry run pytest` and verify it passes before syncing the commands to the prod application
