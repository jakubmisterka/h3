# Tasks

## 1. The values

- [x] 1.1 Add `src/rules/lobby_values.py` with the checks for a timer, a game date, a road setting, a map size and a number of computer players (the forms in the design), with pytest cases for each valid form and each wrong form named in the spec, including `slow+mid`, `mid+slow`, `none`, `L+U`, `XXL`, `117`, `121`, `1214`, `118`, `12:75+06:00+02:00`, `12:00+6:00+02:00` (minutes not zero-padded) and 7 computer players

## 2. Template facts in the catalogue

- [x] 2.1 Let `parse_catalogue` accept optional fields, keeping the rejection of unknown fields, with pytest cases
- [x] 2.2 Read `roads`, `map_size` and `ai` as a default with allowed values (`Choice`), and `sim_turns`, `mirror`, `built_in` and `download`, with the checks in `parse_templates` (default among the allowed values, nothing listed twice, `built_in` only true, `download` an `https://` link and not both, a mirror template's map sizes all with `+U`), each with a message that names the file and the entry, and pytest cases for every scenario of the added `tournament-formats` requirements about template facts
- [x] 2.3 Check that the shipped `data/templates.json` still loads and that `tests/test_shipped_files.py` passes

## 3. Settings in format files

- [x] 3.1 Add `settings` to `formats/schema.json` in the three places (the tournament with only `timer` and `sim_turns`, a template with all five) and read it in `formats.py`, with pytest cases that a good format loads and that each wrong form is reported
- [x] 3.2 Check in `rule_problems` that roads, map size and computer players are among what the template allows, and that a template without allowed values cannot have one chosen, with pytest cases for each scenario of the requirement about what a tournament may choose
- [x] 3.3 Add `src/rules/template_settings.py` with `effective_settings` (template defaults, then the tournament, then the list entry, then the pool entry), with pytest cases for each stacking scenario of the requirement about setting a timer and choosing settings

## 4. The words

- [x] 4.1 Add `src/rules/template_facts.py` with the lines for a `Settings` (mirror, where to get it, timer, map, roads, computer players, simultaneous turns, in that order) and `lobby_lines`, nothing for a fact that is not stated and the link in angle brackets, with pytest cases for each fact alone and for all together
- [x] 4.2 Add the lines to the template reply of `/info`, giving the value most phases use and one line per phase that differs, with pytest cases for each scenario of the modified `mode-info` requirement

## 5. In the thread

- [x] 5.1 Give `Situation` a `settings(template)` method, and add the lines to the rules messages at the start of a match with a named template and to the announcement of a decided game (a pick, and the decider's game), with pytest cases for each scenario of the added `match-setup` requirement, including the same text as before when nothing is stated
- [x] 5.2 Add the lobby lines to the lobby settings, with pytest cases for the two new `game-trade` scenarios

## 6. Description and additional rules

- [x] 6.1 Add `check_text` (not empty, at most 1000 characters) to `src/rules/lobby_values.py`, with pytest cases for a good text, an empty one, spaces only, exactly 1000 characters and 1001
- [x] 6.2 Let a template state `description` and `additional_rules` in the catalogue, with pytest cases for each scenario of the added requirement about a template's description and rules
- [x] 6.3 Let a format state `description` and `additional_rules` for the tournament and `additional_rules` as a template setting (in `formats/schema.json` and `formats.py`), put `additional_rules` into `Settings` and its stacking (catalogue, then the list, then the pool), with pytest cases for the stacking scenarios and for the tournament's texts
- [x] 6.4 Show them in `/info`: the tournament's description and rules in the mode view, and a template's description and rules in its reply, with the phases that differ named, with pytest cases for the new scenarios of `mode-info`
- [x] 6.5 Post the additional rules in the thread when a trade is opened for the first time (not when it is reopened, nothing when there are none), with pytest cases for each scenario of the added `game-trade` requirement

## 7. Documentation, data and the check

- [x] 7.1 Document the fields in `data/README.md` (the default and allowed shape, the road, map size and date notations, what the three parts of the timer mean, `mirror`, `built_in` or `download`, and that a missing field means unknown) and the `settings` of a format in `formats/README.md`, with an example that the tests check
- [x] 7.2 For the maintainers: fill in the facts of the shipped templates in `data/templates.json` and the timer of the tournaments (only what is known), and run `poetry run pytest`
- [x] 7.3 Milestone check in the dev guild: give one template every fact and set a timer in the development format, restart; `/info` shows each as a short line, a match started with that template shows them in the rules, a pick of that template announces them, and the lobby settings show the typed ones; a wrong value in a file stops the start-up with a clear message; a template with nothing stated shows none
- [x] 7.4 Document `description` and `additional_rules` in `data/README.md` and `formats/README.md` (where each can be written, the 1000-character limit, that a template's rules are inherited and replaced like its settings, and that the tournament's own rules are not), with examples that the tests check
