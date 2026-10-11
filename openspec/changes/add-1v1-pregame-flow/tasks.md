# Tasks

How we work: one step at a time. Each step starts with a short explanation of what is built and why, ends with something you can run or look at, and we stop for review before the next step. "Decide" lines name choices that are open until that step. Tests are part of the task that adds the logic, not a separate step.

## 1. Clean start

*Nothing new for players. The project builds and tests can run.*

- [ ] 1.1 Remove the `/hello` command from `src/bot.py` and fix the syntax error (`def main() ->  :` should be `-> None:`); verify `poetry run python -c "import ast; ast.parse(open('src/bot.py', encoding='utf-8').read())"` succeeds, the bot logs in on the dev app, and `/hello` no longer appears in the dev guild
- [ ] 1.2 Add `pytest` (dev group) and a JSON-schema validator with `poetry add`, and verify `poetry run pytest` runs and reports no tests collected instead of an import error
- [ ] 1.3 Create `src/rules/`, `src/commands/`, `formats/`, `data/` and `tests/` and verify a pytest smoke test imports the packages

## 2. Data files

*The two lists everything else refers to: factions (towns) and templates.*

- [ ] 2.1 Add `data/factions.json` with the 12 wiki towns and a loader that rejects duplicate ids and empty names; verify with pytest cases for loading the 12 towns, a duplicate id, an empty name, and finding an entry by id or name ignoring case
- [ ] 2.2 Add `data/templates.json` with JC, 6lm10a and h3dm1 using the same loader; verify with pytest cases for the shipped file and the same error cases

## 3. A format file

*A tournament format as a JSON file, and a check that tells a contributor what is wrong with it.*

- [ ] 3.1 Write `formats/schema.json` for the format shape in the design and verify it accepts a hand-written example and rejects a file missing `phases`
- [ ] 3.2 Implement the format loader and rule validator (pool = steps + 1, picks = best_of - 1, game order covers each game once, unknown fields rejected, every template and faction known) as pure functions, with pytest cases for each scenario of the "Formats are validated" and "Templates come from one catalogue" requirements, including the 9-template and 7-template sequences from the explore session
- [ ] 3.3 Add `formats/el-classico.json` (one phase, BO1, pool of JC / 6lm10a / h3dm1, sequence A ban, B ban, 160% difficulty, default rolls, all factions); verify a pytest test that loads every file in `formats/` passes and that El Classico's sequence leaves exactly one template
- [ ] 3.4 Implement the per-phase allowed factions (default all, restricted subset, unknown faction rejected, a faction added to the catalogue is allowed without other changes), with pytest cases for each scenario of the "Factions come from one catalogue" requirement

Decide: how `game_order` names the games (the design sketches `A_pick`, `B_pick`, `decider`, which is unclear if one player picks twice).

## 4. Trade settings

*What a game's trade is worth: difficulty gives starting gold, default roll rules, which modes can be used.*

- [ ] 4.1 Implement effective trade settings (phase defaults updated by template overrides, with the default roll values 500 gold, 1 roll, 2 bans), with pytest cases for override, no override and default rolls
- [ ] 4.2 Implement the difficulty-to-starting-gold table (80%, 100%, 130%, 160%, 200%) and the default section list per difficulty, and reject an unknown difficulty or a starting gold written in a file; verify with a pytest case per difficulty and per rejection
- [ ] 4.3 Implement the list of selectable modes (archived formats hidden, starting in an archived one refused), with pytest cases for both scenarios

## 5. Info command

*The first command players can use: look up a mode, or a template in a mode. Also how we check format files in Discord.*

- [ ] 5.1 Implement the text for mode info and template info as pure functions, with pytest cases for each scenario of the `mode-info` spec (single and multi-phase, bans and picks in words, agreed template, defaults, override, template in two phases, 200%, unknown mode, template not in the mode, archived mode)
- [ ] 5.2 Load the data files and formats at bot start-up (an invalid file stops the bot with a message naming the file and the problem) and add `/info mode [template]` with autocomplete and an ephemeral reply; verify in the dev guild: `/info` for El Classico, then with `JC`, then break `formats/el-classico.json` on purpose and see the start-up message
- [ ] 5.3 Document how to add a format in `formats/README.md` (fields, an example, how to check it with `poetry run pytest` and `/info`) and verify a newcomer can follow it by copying the El Classico example

## 6. Starting a match

*`/match start` opens a thread and does the coinflip. No memory yet: the thread only shows messages.*

- [ ] 6.1 Implement start validation (self or bot as opponent, phase needed or not, template required and allowed for agreed phases) as pure functions, with pytest cases for each scenario of the `match-setup` spec
- [ ] 6.2 Implement the coinflip with an injectable random source, and pytest cases for a fixed source, each outcome being possible, and fairness over many flips
- [ ] 6.3 Implement `/match start` as a thin handler: create the thread (public or private per format), mention both players, announce the coinflip winner and who acts first. Verify in the dev guild with El Classico, and that the bot has the permissions to create threads, send in them and read their history

Note: no multi-phase or ranked format file exists yet, so those paths are covered by pytest only.

## 7. Remembering the match

*The bot keeps nothing outside the thread. Every step is recorded in the thread and the match is rebuilt from it.*

- [ ] 7.1 Define the event types and their compact text format (a small JSON in an embed footer) in `src/state.py`, with pytest round-trip tests for encode and decode
- [ ] 7.2 Implement rebuilding a match from a list of events as a pure function, with pytest cases for a clean run, a missing start event and a deleted message in the middle (the "cannot be rebuilt" scenario)
- [ ] 7.3 Implement the Discord side: read the bot's own messages in a thread, parse the events, and post an event with its readable text; `/match start` now records its events. Verify in the dev guild that a restarted bot still knows the match
- [ ] 7.4 Add the per-thread lock and verify with a pytest asyncio test that two simultaneous commands on one thread run one after the other
- [ ] 7.5 Reject match commands from non-players and from outside a match thread, with pytest cases for both and a dev-guild check
- [ ] 7.6 Test in the dev guild whether slash commands work in an archived thread; write the result under Open questions in `design.md` and update the `match-setup` spec's open question to match

Decide: how a deleted message is detected (event numbers), and what the embed footer looks like to players.

## 8. Bans and picks

*Template selection, from the first ban to the list of games.*

- [ ] 8.1 Implement the selection step logic (whose turn, which action, template still available, remaining pool, ending with the ordered games) as pure functions, with pytest cases for every scenario of the `template-selection` spec including the 9-template and the 7-template sequences
- [ ] 8.2 Implement `/ban` and `/pick` as thin handlers with autocomplete of the remaining pool, a turn announcement, the remaining-pool message and the final games announcement. Verify a full El Classico selection in the dev guild
- [ ] 8.3 Implement the agreed-template path (skip selection, go straight to the games) and verify with pytest; a ranked match in the dev guild needs a ranked format file, which does not exist yet

## 9. Trade: gold and bids

*The money side of a game's trade: starting gold, the faction bid, the color bid.*

- [ ] 9.1 Implement the gold ledger (payments go to the opponent, whole numbers, balance check) as pure functions, with pytest cases including the worked example (10400 and 9600)
- [ ] 9.2 Implement the trade sections and their order (faction bid, color bid), the first faction pair the bot draws (`draw_pair`, two different allowed factions, uniform, injectable random source), and the report checks (winner is a player, amount within gold, faction in the pair, color red or blue, allowed factions only), with pytest cases for each scenario of the "The trade runs in sections", "The bot generates the faction pair", "Only allowed factions are accepted", "Faction bid is reported", "Color bid is reported" and "The bot keeps the gold" requirements
- [ ] 9.3 Implement `/trade report` and `/trade status` as thin handlers; the trade of the first game starts when selection ends. Verify a full bid sequence in the dev guild

## 10. Trade: rolling

*Paying to reroll the faction pair, or skipping it.*

- [ ] 10.1 Implement rolls (who is eligible, ban limits, cost, a new pair that excludes banned factions), declining, and the implicit decline when a faction bid is reported, with pytest cases (seeded random source) for each scenario of the "A roll costs gold and draws a new pair" and "Each eligible player rolls or declines" requirements
- [ ] 10.2 Implement `/trade roll` and `/trade decline` as thin handlers, including the announcement of the pair, the cost and who may roll. Verify rolling, declining and skipping by bidding in the dev guild

Decide: whether a roll and the new pair it draws are one event; whether a declined roll can be undone.

## 11. Trade: undo, summary and several games

*Correcting a report, the final lobby settings, and trading the games of a match one after another.*

- [ ] 11.1 Implement undo (the latest player report can be undone; rolls and the bot's random results cannot), with pytest cases for each scenario of the "Either player may report, and undo" requirement
- [ ] 11.2 Implement the lobby settings summary as a pure function that builds the text from a finished trade, with a pytest case for the spec's summary scenario
- [ ] 11.3 Implement `/trade undo` as a thin handler and show the summary when a trade finishes. Verify a full game trade in the dev guild
- [ ] 11.4 Make the trade of each game independent (the command targets the first unfinished game unless one is named), with a pytest case, and verify in the dev guild that game 2 can be traded after a pause while game 1 stays complete; this needs a BO3 format file for testing

Decide: how the trade of the next game starts (automatically when the previous ends, or with a command).

## 12. Trade at 200%

*The special case: all-random lobby, no gold, only a toss for color.*

- [ ] 12.1 Implement the 200% color toss section (fair coin from an injectable source, winner chooses red or blue, no gold moves, no roll or faction steps), with pytest cases for each scenario of the "At 200% difficulty only the color is tossed" requirement
- [ ] 12.2 Connect the toss to the trade commands and verify in the dev guild with a temporary 200% format file

## 13. Wrap-up

- [ ] 13.1 Update `CLAUDE.md` (it still says the bot is a single `/hello` command) for the new commands, modules and directories, and verify it matches `git ls-files src formats data`
- [ ] 13.2 Run a complete match in the dev guild from `/match start` to the final lobby settings, including a bot restart in the middle and a reopened thread, and record any rule that needed a guess under the specs' Open question entries
- [ ] 13.3 Run the final `poetry run pytest` and verify it passes before syncing the commands to the prod application
