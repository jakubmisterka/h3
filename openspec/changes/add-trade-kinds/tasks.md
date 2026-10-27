## Milestone A: the trade setting, mirror and computer-player packs

## 1. The trade setting (data)

- [x] 1.1 Add `src/rules/trade_kinds.py`: `TradeKind` (kind, `hero_bans`, `roll_before_heroes`), the reader for the string and object forms with errors in plain words, and `sections(kind, mirror)`, with pytest cases for every form, every default, a bad kind, a bad `hero_bans`, and the sections of every kind and mirror combination
- [x] 1.2 Let a template state `trade` in the catalogue (`catalogue.py`), refusing `standard_with_ai_packs` on a mirror template, with pytest cases for each scenario of the catalogue and mirror checks
- [x] 1.3 Let a format choose `trade` for a template in its list and in a phase's pool (`formats/schema.json`, `formats.py`), refuse it in the tournament's own settings, and stack it in `Settings`/`effective_settings` (catalogue, then list, then pool), with pytest cases for the scenarios of "A template and a tournament choose how a game is traded"
- [x] 1.4 Add the format checks that need no hero data: packs in a phase allowing fewer than eight towns, `hero_bans` with `roll_before_heroes` false, with pytest cases

## 2. Sections as data (no change in behavior)

- [x] 2.1 Make `Trade.section`, the prompts and the replay work from the sections of the trade's kind instead of the fixed list, passing the kind into `new_trade`/`replay_trades` from the situation; every existing test stays unchanged and green
- [x] 2.2 Change the readers of the trade records in `state.py` to return all the quoted words of a draw and a roll, split by the draw size of the kind in `rules/trade.py`, so a record with two words is a standard draw as before; pytest cases that parse what the wording functions write, and old-style records
- [x] 2.3 Add the `Draw` value (towns, packs, heroes) and the draw functions with an injected random source (`draw_town`, `draw_with_packs`), with pytest cases for distinctness, fairness, banned towns and refusals when too few towns are left

## 3. The mirror trade

- [x] 3.1 Draw one town, let a roll ban the standing town and redraw, make the color bid the only bid, and word the announcement, the roll and the report, with pytest cases for each scenario of the mirror requirement
- [x] 3.2 Make the lobby settings of a mirror trade say the one town both play, with pytest cases; make `/trade roll` need no town in a mirror and `/trade report` refuse a town with a message that says the color bid is next; pytest cases through the commands
- [x] 3.3 Make `/match status` and `next_steps` name the right section for a mirror trade, and undo work on its steps, with pytest cases
- [x] 3.4 Make a skip last only until the towns change (the other player's roll clears it, so the one who skipped can roll again), with pytest cases for each scenario of "Each eligible player rolls or skips the roll", the wording of the refusal and the description of `/trade skip-roll`

## 4. The trade with computer-player packs

- [x] 4.1 Draw the pair and two packs, redraw them all on a roll that bans only towns of the pair, refuse a roll that leaves fewer than two towns for the pair (a banned town may come up in a pack), and word the announcement and the roll, with pytest cases for each roll scenario
- [x] 4.2 Add the `pack_bid` record (`pb`) and its report as `pack1`/`pack2`, between the town and the color bid, with pytest cases for each scenario of the pack bid
- [x] 4.3 Make the lobby settings of a packs trade list each player's pack, and `/match status`, `next_steps` and undo handle the pack bid, with pytest cases
- [x] 4.5 Say what comes next after a game's trade is done (the next ban or pick, the game to trade, or that every game is traded), with pytest cases for each scenario of "After a game's trade the thread says what is next"
- [x] 4.4 Make the `choice` of `/trade report` and its autocomplete follow the section that is expected (town, pack, color), with pytest cases for the suggestions and the refusals

## Milestone B: heroes and the roulette

## 5. The hero catalogue

- [ ] 5.1 Add `data/heroes.json` loading (`id`, `name`, `town`, `link`) with the checks of "Heroes come from one catalogue", `Registry.heroes` (empty by default) and `load_registry`, with pytest cases for each scenario
- [ ] 5.2 Let a template list `banned_heroes` and check them against the hero catalogue, with pytest cases for each scenario
- [ ] 5.3 Add the format checks that need hero data (a roulette needs heroes, and every allowed town keeps enough of them), passing the hero catalogue into format validation as an optional argument, with pytest cases

## 6. The roulette trade

- [ ] 6.1 Add the hero rules in plain functions: the heroes of a town, who may ban when (the coinflip winner first), how many, which heroes cannot be banned, and `draw_heroes` (mirror: two of the town; otherwise one per town of the pair) that skips banned heroes and the template's `banned_heroes`, with pytest cases for each ban scenario and for the draw
- [ ] 6.2 Add the records `heroes_banned` (`hb`) and `heroes_drawn` (`hd`) to `state.py` and the replay checks of the draw, with pytest cases for reading, writing and every replay refusal
- [ ] 6.3 Wire the roulette into the trade: the ban step, `automatic_steps` that posts the draw when it is due (at the end of the roll section, after the last ban, or at the opening where nobody can roll), and the refusal of a bid before the draw, with pytest cases for each scenario of "A roulette trade draws heroes after the rolls"
- [ ] 6.4 Make a roulette that is not a mirror use the town bid and the color bid, showing each town with its hero in the announcements, the status and the lobby settings, with pytest cases for its scenario
- [ ] 6.5 Add the `first_choice_bid` record (`fb`) for the mirror roulette, its report (`hero` or `color`), its wording and the lobby settings that say who chooses what, with pytest cases for each scenario
- [ ] 6.6 Let `roll_before_heroes: false` draw the heroes with the towns and redraw them on every roll, with pytest cases for each scenario
- [ ] 6.7 Add `/trade ban-heroes` with up to three hero options and their autocomplete, and make the `choice` of `/trade report` offer `hero`/`color`, with pytest cases through the commands (the description of every option stays within 100 characters)
- [ ] 6.8 Refuse an undo that starts at a hero draw and say to undo from the step before it, and make `/match status` and `next_steps` name every roulette section, with pytest cases for each undo scenario

## 7. Info, documentation and the check

- [ ] 7.1 Show the trade kind in `/info <mode> <template>` (nothing for a standard trade, the kind most phases use and the phases that differ otherwise), with pytest cases for each scenario of the added mode-info requirement
- [ ] 7.2 Document `trade`, `banned_heroes` and `data/heroes.json` in `data/README.md`, the trade setting and an example of `additional_rules` for the mirror hero procedure in `formats/README.md`, with examples that the tests check, and update `src/rules/README.md` and `CLAUDE.md`
- [ ] 7.3 For the maintainers: fill in `data/heroes.json` from the community wiki, the `banned_heroes` of the templates that exclude heroes, the `trade` of Sapphire and the other templates, and the trade of the Mistrzostwa Polski 2026 phases
- [x] 7.4 Milestone check A in the dev guild: a mirror game (roll, color bid, lobby settings) and a game with packs (roll, town, pack and color bids, undo of the pack bid)
- [ ] 7.5 Milestone check B in the dev guild: a mirror roulette and a roulette with a pair, with and without hero bans, with `roll_before_heroes` false, and an undo from a hero ban
