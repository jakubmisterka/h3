## 1. The format

- [x] 1.1 Add `fixed` to `template_selection.type` in `formats/schema.json` and to the parsing of a phase (`Phase.fixed`, no steps), with pytest cases for a fixed phase and for steps in a fixed phase
- [x] 1.2 Refuse a fixed phase that does not have exactly one template (the phase's `pool`, else the tournament's list), naming the phase, with pytest cases for each scenario of "A fixed phase has exactly one template"
- [x] 1.3 Document `fixed` in `formats/README.md` with a tested example (a one-template BO3 tournament), and add it to the shipped-files tests if a shipped format uses it

## 2. Starting a match

- [x] 2.1 `choose_template` takes no name in a fixed phase, accepts the phase's template and refuses another one listing the phase's template, with pytest cases
- [x] 2.2 `begin_match` for a fixed phase posts the format (`Format: BO3`) and what is stated about the template, does the coinflip and opens the trade of game 1, with pytest cases on the fake thread

## 3. Playing the games

- [x] 3.1 Make the games of a fixed phase the template repeated `best_of` times in `situation_of`, and use the number of games instead of `has_selection` where the code means "only one game" (next steps after a trade, `/match status`), with pytest cases for the next game, for every game traded, and for the overview
- [x] 3.2 Make `/ban` and `/pick` say a fixed phase has no bans or picks, and make the undo and status texts work for it, with pytest cases
- [x] 3.3 Say in `/info` for the mode that all games are played on the template instead of the Template Selection line, with pytest cases

## 4. Check

- [ ] 4.1 Milestone check in the dev guild: add a one-template BO3 test format, play the three trades, ask for `/match status`, try `/ban`, and undo from the second game
