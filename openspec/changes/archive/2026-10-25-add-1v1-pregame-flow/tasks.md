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

- [x] 3.1 Define the records the bot writes and how each is written into a message (a tag `[#<number> <code>]` at the start, the data read from the text in a fixed order) and read back, in a plain module, with pytest tests for the tag and for reading each record type
- [x] 3.2 Post a record as one message and read the thread back (keep only the bot's own messages, parse the tagged ones), checking before sending that the message reads back as the same record; `/match start` now posts a "match started" record
- [x] 3.3 Add `/match status` for a match thread that shows what the bot read back, as a simple list for now
- [x] 3.4 Milestone check A: start a match, stop the bot, start it again, and `/match status` still lists the record
- [x] 3.5 Milestone check B, skipped by decision: archived threads are not tested. Threads stay open for 7 days of silence, which we assume is enough. The open question stays recorded in `design.md` and the `match-setup` spec, to be revisited if players run into archived threads

Decided: each step is one message that starts with a tag `[#n code]`; the data is read from the text in a fixed order, so the wording after the data is free. See `src/state.py`.

## 4. Milestone: only the two players act

*Match commands are accepted only inside the match thread and only from its two players.*

- [x] 4.1 Add the guard that every match command goes through (right thread, one of the two players), with pytest cases for each scenario of the "Only the two players act" requirement
- [x] 4.2 Milestone check in the dev guild: a third account's command in the thread is refused and changes nothing; a command outside a thread says to use the match thread

Decide: whether reading (`/match status`) is open to everyone or only to the players.

## 5. Milestone: a format file the bot checks

*Tournament formats as JSON files, and a check that tells a contributor what is wrong with a file.*

- [x] 5.1 Add `data/towns.json` with the 12 wiki towns and a loader that rejects duplicate ids and empty names, with pytest cases for loading the 12, a duplicate id, an empty name, and finding an entry by id or name ignoring case
- [x] 5.2 Add `data/templates.json` with JC, 6lm10a and h3dm1 using the same loader (each template also states its difficulty, 160% for all three, see 5.4a), with pytest cases for the shipped file
- [x] 5.3 Add a JSON-schema validator with `poetry add` and write `formats/schema.json` for the format shape in the design; verify it accepts a hand-written example and rejects a file missing `phases`
- [x] 5.4 Implement the format loader and rule validator (pool size = number of steps, the decider is last and has no player, picks plus decider = best_of, unknown fields rejected, every template and town known), with pytest cases for each scenario of the "Formats are validated" and "Templates come from one catalogue" requirements, including the 9-template and 7-template sequences from the explore session
- [x] 5.4a Move the difficulty to the templates: `data/templates.json` states each template's difficulty (the loader takes the extra fields a catalogue requires), the format schema loses `trade` and difficulty and gains the optional `roll_rules`, and the code, specs and tests follow; verify the whole test suite passes and no format file mentions difficulty
- [x] 5.4b Restructure the templates: the format lists the tournament's templates once, each phase selects its pool from them (all of them when it states none), and roll rules can be written for the tournament, a template, or a template in one phase; the schema, loader, specs and tests follow; verify the whole test suite passes
- [x] 5.5 Add `formats/el-classico.json` (templates JC / 6lm10a / h3dm1, one BO1 phase that uses all of them, sequence A ban, B ban, decider, default roll rules, all towns); verify a pytest test that loads every file in `formats/` passes (a development format that real tournaments will replace)
- [x] 5.6 Implement the allowed towns (default all, a tournament list, a phase list that replaces it, restricted subset, unknown town rejected, a town added to the catalogue is allowed without other changes), with pytest cases for each scenario of the "Towns come from one catalogue" requirement
- [x] 5.7 Load the data files and formats when the bot starts; an invalid file stops the bot with a message naming the file and the problem
- [x] 5.8 Milestone check: the bot starts with the development format (El Classico); change its `best_of` from 1 to 3 and the bot refuses to start and says why (a best-of-3 needs 3 games, the sequence gives 1); fix it and it starts again

Decided: there is no separate game order. The sequence ends with a `decider` step (the template that is left), and the games are played in the order of the picks, then the decider. A best-of-2 league phase is simply two picks and no decider.

## 6. Milestone: `/info`

*Look up a mode, or a template in a mode. Also how we check format files in Discord.*

- [x] 6.1 Implement the effective roll rules of a template (built-in defaults 500 gold, 1 roll, 2 bans, updated by the tournament's `roll_rules`, then by the template's entry in the tournament list, then by its entry in the phase's pool), with pytest cases for each level, field by field merging, and the defaults
- [x] 6.2 Implement the difficulty-to-starting-gold table (80%, 100%, 130%, 160%, 200%) and the default section list per difficulty, and refuse a template whose difficulty is not in the table; verify with a pytest case per difficulty and for the refusal
- [x] 6.3 Implement the list of selectable modes (archived formats hidden for new matches, starting in an archived one refused), with pytest cases for both
- [x] 6.4 Implement the text for mode info and template info as pure functions, with pytest cases for each scenario of the `mode-info` spec (single and multi-phase with nothing repeated, one phase only, the template selection line such as "AB: A bans, B bans, then decider", agreed template, defaults, the same in every phase, differing rules listed per phase, 200%, unknown mode, template not in the mode, archived mode)
- [x] 6.5 Add `/info mode [template] [phase]` as a thin handler with autocomplete and an ephemeral reply
- [x] 6.6 Document how to add a format in `formats/README.md` (fields, an example, how to check it with `poetry run pytest` and `/info`) and verify a newcomer can follow it by copying an existing format file
- [x] 6.7 Milestone check in the dev guild: `/info` for the development format, then with `JC`, then an unknown mode and a template that is not in the mode; change JC's difficulty in `data/templates.json` to 130, restart, and `/info` shows 130% difficulty for JC

## 7. Milestone: a real match start with the coinflip

*`/match start` now uses a mode from the formats and the bot does the coinflip.*

- [x] 7.1 Implement start validation (phase needed or not, template required and allowed for agreed phases) as pure functions, with pytest cases for each scenario of the `match-setup` spec
- [x] 7.2 Implement the coinflip with an injectable random source, with pytest cases for a fixed source, each outcome being possible, and fairness over many flips
- [x] 7.3 Extend `/match start` to `mode opponent [phase] [template]`: thread visibility comes from the format (the temporary `private` option is removed), the coinflip is recorded and announced with who acts first
- [x] 7.4 Rebuild a match from its records as a pure function (players, coinflip winner) that refuses to guess: a missing start record, a gap in the record numbers (a deleted message) and a second start are reported in words; `/match status` uses it. Verify with pytest cases for a clean run and each failure
- [x] 7.5 Milestone check in the dev guild: start a match in the development format, see the coinflip winner announced, restart the bot and `/match status` still shows it; delete the coinflip message of a test match and `/match status` says a message is missing. Multi-phase and ranked modes have no format file yet, so they are covered by pytest only

## 8. Milestone: bans and picks to the list of games

*Template selection from the first ban to the games to play.*

- [x] 8.1 Implement the selection logic (whose turn, which action, template still available, remaining pool, ending with the ordered games) as pure functions, with pytest cases for every scenario of the `template-selection` spec including the 9-template and the 7-template sequences
- [x] 8.2 Add the per-thread lock, so two commands on one match thread at the same moment run one after the other (`poetry add --group dev pytest-asyncio` for the test); verify with a pytest asyncio test. It is built here because `/ban` is the first command that changes a match
- [x] 8.3 Add `/ban` and `/pick` as thin handlers with autocomplete of the remaining pool, a turn announcement, the remaining-pool message and the final games announcement
- [x] 8.4 Implement the agreed-template path (skip selection, go straight to the games), covered by pytest
- [x] 8.5 Milestone check in the dev guild: a full selection in the development format; the wrong player is refused; a template that is already banned is refused; restart the bot between the two bans and it continues

## 9. Milestone: the trade, bids only

*The money side of a game's trade: starting gold, the town bid, the color bid.*

- [x] 9.0 Let a record tag carry the game (`[#7 tr g1]`) as an optional marker, parsed in `state.py` and kept in one numbered sequence with the other records, with pytest cases
- [x] 9.1 Implement the gold ledger (payments go to the opponent, whole numbers, balance check) as pure functions, with pytest cases including the worked example (10400 and 9600)
- [x] 9.2 Implement the games known so far (the picks in order, the decider once selection is done), the open trade (the latest start or reopening), and the trade sections and their order (town bid, color bid), the first town pair the bot draws (two different allowed towns, equal chances, injectable random source), and the report checks (winner is a player, amount within gold, town in the pair, color red or blue, allowed towns only), with pytest cases for the "The trade runs in sections", "The bot generates the town pair", "Only allowed towns are accepted", "Town bid is reported", "Color bid is reported" and "The bot keeps the gold" requirements
- [x] 9.3 Add `/trade start [game]` (a game number or a template; closes the open trade as incomplete, reopens a trade started before) and `/trade report` as thin handlers, announce "Game N is <template>: start its trade with /trade start" when a pick makes a game known, show gold as the difference from the starting gold (the starting gold only at the start), post the lobby settings when the color bid is reported, and extend `/match status` into the overview (next selection step, every started trade with its section and gold)
- [x] 9.4 Milestone check in the dev guild: play the bids of one game; a bid above the winner's gold, a town outside the pair and a color before the town are each refused; the gold shown after each report is right


## 10. Milestone: rolling

*Paying to reroll the town pair, or skipping the roll.*

- [x] 10.0 Add the roll and the skipped-roll record types (a roll and the new pair it drew are one record), read back from the thread, with pytest cases
- [x] 10.1 Implement rolls (who is eligible, ban limits, cost, a new pair that excludes banned towns), skipping, and the implicit skip when a town bid is reported, with pytest cases (seeded random source) for each scenario of the "A roll costs gold and draws a new pair" and "Each eligible player rolls or skips the roll" requirements
- [x] 10.2 Add `/trade roll [ban_1] [ban_2]` and `/trade skip-roll` as thin handlers, including the announcement of the pair, the cost and who may roll
- [x] 10.3 Milestone check in the dev guild: roll with bans, skip the roll with the command, skip it by bidding, and try rolling twice; the gold and the new pair are right each time

Decided: a roll and the new pair it draws are one record; a skipped roll can be undone in milestone 11, but only while it is the latest action.

## 11. Milestone: undo and several games

*Going back after a mistake with both players' consent, the final lobby settings, and trading the games of a match one after another.*

- [x] 11.0 Add the undo request and undone record types and `effective_records` (the records that still count after the undos), read back from the thread and used by the rebuilt match, with pytest cases
- [x] 11.1 Implement the undo logic as pure functions (what a request undoes, the checks, the pending request, the text of the request and of the confirmation), with pytest cases for each scenario of the "Either player can ask to undo, and the other must agree" requirement
- [x] 11.2 Implement the lobby settings summary as a pure function that builds the text from a finished trade, with a pytest case for the spec's summary scenario (done with milestone 9, so every trade ends with it)
- [x] 11.3 Add `/match undo [from]` as a thin handler (a plain number option; agreeing needs no number), mark the undone records in the match status, and show where the match stands after an undo
- [x] 11.4 Check that games trade one after another (a finished trade stays finished while the next one opens), with a pytest case
- [x] 11.5 Milestone check in the dev guild with a best-of-3 format: undo a bid, undo a ban with a trade already started, undo a roll, let a request lapse, and confirm from the wrong player; finish game 1 and read the summary, then trade game 2 after a pause with game 1 staying complete; open game 2 while game 1 is half done and reopen game 1

## 12. Milestone: start straight at the trade

*Naming a template when starting a match skips the bans and picks: one game, straight to its trade.*

- [x] 12.1 Accept a named template in any phase (it must be in the phase's pool; required where players agree), open the trade of its game when the match starts, and treat a match with a named template as one game with no selection: the situation, the announcements at the start, the refusal of `/ban` and `/pick`, the overview and the choice of a game, with pytest cases for each scenario of the "A match can start straight at the trade with a named template" requirement
- [x] 12.2 Offer the phase's templates when typing the template option for every phase, and say after the lobby settings that it was the only game
- [x] 12.3 Milestone check in the dev guild: start a match in the development format naming a template: the bot opens the trade itself, with no command needed; `/ban` is refused; a template outside the pool is refused and no thread appears; after the lobby settings the bot says it was the only game

### Left out of this change

Games on 200% difficulty (an all-random lobby, no gold, only a toss for color) are left to a follow-up OpenSpec change. Until then the bot says the trade of such a game is not available.

## 13. Wrap-up

- [x] 13.1 Update `CLAUDE.md` (it still says the bot is a single `/hello` command) for the new commands, modules and directories, and verify it matches `git ls-files src formats data`
- [x] 13.2 Run a complete match in the dev guild from `/match start` to the final lobby settings, including a bot restart in the middle and a reopened thread, and record any rule that needed a guess under the specs' Open question entries
- [x] 13.3 Run the final `poetry run pytest` and verify it passes before syncing the commands to the prod application
