# Tasks

How we work: one milestone at a time. Each milestone starts with a short explanation of what is built and why, and ends with a **milestone check**: something you try yourself in the dev guild. We stop there and review before the next milestone. Folders and dependencies are added when the first file or task needs them. Tests are part of the task that adds the logic. "Decide" lines name choices that stay open until that milestone.

The riskiest unknowns are about Discord (threads, reading messages back, archived threads), so milestones 2 to 4 prove them in practice before any tournament rules are written.

## 1. Milestone: the bot starts cleanly

*Nothing new for players. A working base to build on.*

- [x] 1.1 Remove the `/hello` command from `src/bot.py` and fix the syntax error (`def main() ->  :` should be `-> None:`); verify the file parses, the bot logs in on the dev app, and `/hello` no longer appears in the dev guild
- [x] 1.2 Add `pytest` as a dev dependency with `poetry add --group dev` and verify `poetry run pytest` runs and reports no tests collected instead of an import error
- [x] 1.3 Milestone check: the bot logs in as the dev app, `/hello` is gone, and `poetry run pytest` runs. Review before milestone 2

## 2. Milestone: create a thread in the channel

*The first thing players see. Proves that the bot can open a match thread where the command was run.*

- [x] 2.1 Add `/match start opponent` as a thin handler: in the channel where it is run, create a public thread named after the two players, mention both, and post a first message. The check that the opponent is neither yourself nor a bot is a plain function with pytest cases for both refusals (the `match-setup` spec's "Invalid opponent")
- [x] 2.2 Add a temporary `private` option to try a private thread (only the two players, the bot and moderators), adding both players to it; it is replaced by the format's setting in milestone 7
- [x] 2.3 Show a clear message when Discord refuses (missing permission, or the command run inside a thread), and note in `CLAUDE.md` which permissions the bot turned out to need
- [x] 2.4 Milestone check in the dev guild: the public thread appears with both players mentioned; the private thread cannot be opened by a third account; yourself or a bot as opponent is refused; running it inside a thread is refused politely; removing the thread permission from the bot gives the clear message

## 3. Milestone: the bot can read back what it wrote

*The design keeps no database: the match lives in the thread. If reading it back does not work, the design changes, so this is proven early.*

- [ ] 3.1 Define the records the bot writes (events) and their compact text format in a plain module, with pytest round-trip tests for encoding and decoding
- [ ] 3.2 Post a record with its readable text, and read the thread back (keep only the bot's own messages, decode the records); `/match start` now posts a "match started" record
- [ ] 3.3 Add `/match status` for a match thread that shows what the bot read back, as a simple list for now
- [ ] 3.4 Milestone check A: start a match, stop the bot, start it again, and `/match status` still lists the record
- [ ] 3.5 Milestone check B: let the thread archive (or close it by hand) and run `/match status` in it; write the result under Open questions in `design.md` and update the `match-setup` spec's open question to match
- [ ] 3.6 Rebuild a match from its records as a pure function that detects a missing start record and a deleted message in the middle (records are numbered), with pytest cases for a clean run and both failures. Milestone check C: delete one of the bot's messages in a dev thread and see the "cannot be rebuilt" message
- [ ] 3.7 Add the per-thread lock (`poetry add --group dev pytest-asyncio` for the test) and verify with a pytest asyncio test that two simultaneous commands on one thread run one after the other

Decide: what a record looks like to players in the thread (the machine part sits in an embed footer in the current design), and how the numbering works.

## 4. Milestone: only the two players act

*Match commands are accepted only inside the match thread and only from its two players.*

- [ ] 4.1 Add the guard that every match command goes through (right thread, one of the two players), with pytest cases for each scenario of the "Only the two players act" requirement
- [ ] 4.2 Milestone check in the dev guild: a third account's command in the thread is refused and changes nothing; a command outside a thread says to use the match thread

Decide: whether reading (`/match status`) is open to everyone or only to the players.

## 5. Milestone: a format file the bot checks

*Tournament formats as JSON files, and a check that tells a contributor what is wrong with a file.*

- [ ] 5.1 Add `data/factions.json` with the 12 wiki towns and a loader that rejects duplicate ids and empty names, with pytest cases for loading the 12, a duplicate id, an empty name, and finding an entry by id or name ignoring case
- [ ] 5.2 Add `data/templates.json` with JC, 6lm10a and h3dm1 using the same loader, with pytest cases for the shipped file
- [ ] 5.3 Add a JSON-schema validator with `poetry add` and write `formats/schema.json` for the format shape in the design; verify it accepts a hand-written example and rejects a file missing `phases`
- [ ] 5.4 Implement the format loader and rule validator (pool = steps + 1, picks = best_of - 1, game order covers each game once, unknown fields rejected, every template and faction known), with pytest cases for each scenario of the "Formats are validated" and "Templates come from one catalogue" requirements, including the 9-template and 7-template sequences from the explore session
- [ ] 5.5 Add `formats/el-classico.json` (one phase, BO1, pool of JC / 6lm10a / h3dm1, sequence A ban, B ban, 160% difficulty, default rolls, all factions); verify a pytest test that loads every file in `formats/` passes and that El Classico's sequence leaves exactly one template
- [ ] 5.6 Implement the per-phase allowed factions (default all, restricted subset, unknown faction rejected, a faction added to the catalogue is allowed without other changes), with pytest cases for each scenario of the "Factions come from one catalogue" requirement
- [ ] 5.7 Load the data files and formats when the bot starts; an invalid file stops the bot with a message naming the file and the problem
- [ ] 5.8 Milestone check: the bot starts with El Classico; make its pool one template too large and the bot refuses to start and says why; fix it and it starts again

Decide: how `game_order` names the games (the design sketches `A_pick`, `B_pick`, `decider`, which is unclear if one player picks twice).

## 6. Milestone: `/info`

*Look up a mode, or a template in a mode. Also how we check format files in Discord.*

- [ ] 6.1 Implement effective trade settings (phase defaults updated by template overrides, with the default roll values 500 gold, 1 roll, 2 bans), with pytest cases for override, no override and default rolls
- [ ] 6.2 Implement the difficulty-to-starting-gold table (80%, 100%, 130%, 160%, 200%) and the default section list per difficulty, and reject an unknown difficulty or a starting gold written in a file; verify with a pytest case per difficulty and per rejection
- [ ] 6.3 Implement the list of selectable modes (archived formats hidden for new matches, starting in an archived one refused), with pytest cases for both
- [ ] 6.4 Implement the text for mode info and template info as pure functions, with pytest cases for each scenario of the `mode-info` spec (single and multi-phase, bans and picks in words, agreed template, defaults, override, template in two phases, 200%, unknown mode, template not in the mode, archived mode)
- [ ] 6.5 Add `/info mode [template]` as a thin handler with autocomplete and an ephemeral reply
- [ ] 6.6 Document how to add a format in `formats/README.md` (fields, an example, how to check it with `poetry run pytest` and `/info`) and verify a newcomer can follow it by copying the El Classico example
- [ ] 6.7 Milestone check in the dev guild: `/info` for El Classico, then with `JC`, then an unknown mode and a template that is not in the mode; change El Classico's difficulty to 130, restart, and `/info` shows 15000 gold

## 7. Milestone: a real match start with the coinflip

*`/match start` now uses a mode from the formats and the bot does the coinflip.*

- [ ] 7.1 Implement start validation (phase needed or not, template required and allowed for agreed phases) as pure functions, with pytest cases for each scenario of the `match-setup` spec
- [ ] 7.2 Implement the coinflip with an injectable random source, with pytest cases for a fixed source, each outcome being possible, and fairness over many flips
- [ ] 7.3 Extend `/match start` to `mode opponent [phase] [template]`: thread visibility comes from the format (the temporary `private` option is removed), the coinflip is recorded and announced with who acts first
- [ ] 7.4 Milestone check in the dev guild: start an El Classico match, see the coinflip winner announced, restart the bot and `/match status` still shows it. Multi-phase and ranked modes have no format file yet, so they are covered by pytest only

## 8. Milestone: bans and picks to the list of games

*Template selection from the first ban to the games to play.*

- [ ] 8.1 Implement the selection logic (whose turn, which action, template still available, remaining pool, ending with the ordered games) as pure functions, with pytest cases for every scenario of the `template-selection` spec including the 9-template and the 7-template sequences
- [ ] 8.2 Add `/ban` and `/pick` as thin handlers with autocomplete of the remaining pool, a turn announcement, the remaining-pool message and the final games announcement
- [ ] 8.3 Implement the agreed-template path (skip selection, go straight to the games), covered by pytest
- [ ] 8.4 Milestone check in the dev guild: a full El Classico selection; the wrong player is refused; a template that is already banned is refused; restart the bot between the two bans and it continues

## 9. Milestone: the trade, bids only

*The money side of a game's trade: starting gold, the faction bid, the color bid.*

- [ ] 9.1 Implement the gold ledger (payments go to the opponent, whole numbers, balance check) as pure functions, with pytest cases including the worked example (10400 and 9600)
- [ ] 9.2 Implement the trade sections and their order (faction bid, color bid), the first faction pair the bot draws (two different allowed factions, equal chances, injectable random source), and the report checks (winner is a player, amount within gold, faction in the pair, color red or blue, allowed factions only), with pytest cases for the "The trade runs in sections", "The bot generates the faction pair", "Only allowed factions are accepted", "Faction bid is reported", "Color bid is reported" and "The bot keeps the gold" requirements
- [ ] 9.3 Add `/trade report` and `/trade status` as thin handlers; the trade of the first game starts when selection ends
- [ ] 9.4 Milestone check in the dev guild: play the bids of one game; a bid above the winner's gold, a faction outside the pair and a color before the faction are each refused; the gold shown after each report is right

Decide: how the trade of a game starts and how the next game's trade starts.

## 10. Milestone: rolling

*Paying to reroll the faction pair, or skipping the roll.*

- [ ] 10.1 Implement rolls (who is eligible, ban limits, cost, a new pair that excludes banned factions), declining, and the implicit decline when a faction bid is reported, with pytest cases (seeded random source) for each scenario of the "A roll costs gold and draws a new pair" and "Each eligible player rolls or declines" requirements
- [ ] 10.2 Add `/trade roll` and `/trade decline` as thin handlers, including the announcement of the pair, the cost and who may roll
- [ ] 10.3 Milestone check in the dev guild: roll with bans, decline, skip the roll by bidding, and try rolling twice; the gold and the new pair are right each time

Decide: whether a roll and the new pair it draws are one record; whether a declined roll can be undone.

## 11. Milestone: undo, the summary and several games

*Correcting a report, the final lobby settings, and trading the games of a match one after another.*

- [ ] 11.1 Implement undo (the latest player report can be undone; rolls and the bot's random results cannot), with pytest cases for each scenario of the "Either player may report, and undo" requirement
- [ ] 11.2 Implement the lobby settings summary as a pure function that builds the text from a finished trade, with a pytest case for the spec's summary scenario
- [ ] 11.3 Add `/trade undo` as a thin handler and show the summary when a trade finishes
- [ ] 11.4 Make the trade of each game independent (the command targets the first unfinished game unless one is named), with a pytest case
- [ ] 11.5 Milestone check in the dev guild with a temporary BO3 format file: undo a bid, try to undo a roll, finish game 1 and read the summary, then trade game 2 after a pause with game 1 staying complete

## 12. Milestone: trade at 200%

*The special case: an all-random lobby, no gold, only a toss for color.*

- [ ] 12.1 Implement the 200% color toss section (fair coin from an injectable source, winner chooses red or blue, no gold moves, no roll or faction steps), with pytest cases for each scenario of the "At 200% difficulty only the color is tossed" requirement
- [ ] 12.2 Connect the toss to the trade commands
- [ ] 12.3 Milestone check in the dev guild with a temporary 200% format file: the toss is announced, only the winner chooses the color, and the summary leaves out factions and gold

## 13. Wrap-up

- [ ] 13.1 Update `CLAUDE.md` (it still says the bot is a single `/hello` command) for the new commands, modules and directories, and verify it matches `git ls-files src formats data`
- [ ] 13.2 Run a complete match in the dev guild from `/match start` to the final lobby settings, including a bot restart in the middle and a reopened thread, and record any rule that needed a guess under the specs' Open question entries
- [ ] 13.3 Run the final `poetry run pytest` and verify it passes before syncing the commands to the prod application
