# Design

## Context

Templates live in `data/templates.json` and are loaded by `src/rules/catalogue.py`. The loader demands that every entry has exactly `id`, `name` and the required extra fields (`difficulty` for templates), so a field that may be missing has no place yet. Formats are JSON files checked by `formats/schema.json` and `src/rules/formats.py`; a format can already set roll rules in three places (the tournament, a template in its list, a template in a phase's pool), and `src/rules/roll_rules.py` stacks them with the most specific winning. Settings reuse that shape. See proposal.md for what players see.

Where the template of a game is announced today, all in plain functions in `src/rules/`:
- `/info` for a template: `template_info` in `info.py`.
- The rules messages at the start of a match: `rules_announcement` in `start.py`.
- The announcement that a pick (or the last ban) decided a game: `_start_hint` in `situation.py`, used by `next_steps`.
- The lobby settings: `summary` in `trade.py`.

## Goals / Non-Goals

**Goals:**
- Template facts with defaults and allowed values, tournament settings that stack like roll rules, and checks that tell a contributor exactly what is wrong.
- One function that gives the settings of a template in a phase, and one place that words them, so every message says the same thing the same way.
- A template and a format without any of this produce exactly the messages they produce today.

**Non-Goals:**
- Filling in real facts (the maintainers do).
- Anything that runs a clock, or the trades that mirror and Sapphire templates need.

## Decisions

### 1. Small value modules

`src/rules/lobby_values.py` has the five forms and their checks, each raising `ValueError` with the expected form and the part that is wrong:
- the timer: three `mm:ss` parts joined by `+`, each part with two digits of minutes and two digits of seconds, zero-padded (`06:00`, never `6:00`), seconds below 60; kept as written and shown as written;
- the game date: digits, the last the day (1 to 7), the one before the week (1 to 4), the rest the month (1 or more); kept as written;
- a road setting: `none`, or `slow`, `mid`, `fast` joined by `+` in that order (so `slow+mid`, never `mid+slow`);
- a map size: `S`, `M`, `L`, `XL`, `H`, `XH` or `G`, with an optional `+U`;
- computer players: a whole number from 0 to 6.

*Alternative:* parse the timer and the date into numbers. Rejected: nothing in the bot computes with them, and re-formatting could change what a player sees compared to what the contributor wrote.

### 2. Optional fields, and a default with what is allowed

`parse_catalogue` gets a second mapping, `optional_fields`: name to a checker. For templates, `roads`, `map_size` and `ai` are an object `{"default": ..., "allowed": [...]}` and become a small frozen dataclass `Choice(default, allowed)`; `sim_turns` is a string; `mirror` and `built_in` are booleans; `download` is a string. `details` holds the fields that are present. The checks that compare fields run in `parse_templates`, next to the difficulty check, with messages that name the file, the entry number and the id:
- the default is in the allowed list, and no value is listed twice;
- `built_in` only as true, `download` an `https://` link, not both;
- a mirror template's default and allowed map sizes all have `+U`.

*Alternative:* describe the catalogue with a JSON Schema as formats are. Rejected for now: the catalogue is small and its other checks (supported difficulties) are already Python; two mechanisms for one file would be harder to follow.

### 3. Settings in the format file stack like roll rules

A `settings` object may appear in three places, as `roll_rules` does: on the tournament (only `timer` and `sim_turns`), on a template in the tournament's list, and on a template in a phase's pool (all five). `formats/schema.json` has two shapes, one for the tournament and one for a template. `Format` and `TemplateEntry` keep the settings as written, and `src/rules/template_settings.py` has `effective_settings(fmt, phase, template_id, catalogue)`, which starts from the template's defaults and applies the tournament's, then the list entry's, then the pool entry's, setting by setting. It returns a frozen `Settings` with `timer`, `roads`, `map_size`, `ai` and `sim_turns` (each `None` when unknown), next to the template's `mirror` and where to get it.

`rule_problems` in `formats.py` checks every choice: the form of each value, and that roads, map size and computer players are among the values the template allows (a template with no allowed values cannot have one chosen). The message names the format, the template, the setting and what is allowed.

### 4. One module words the settings

`src/rules/template_facts.py` takes a `Settings` and returns lines in a fixed order, one per stated fact:
- `Mirror: both players get the same town`
- `Built into HotA` or `Download: <link>` (the link in angle brackets so Discord does not unfold it)
- `Timer: 12:00+06:00+02:00`
- `Map: L+U`
- `Roads: slow+mid` or `No roads`
- `AI players: 3` or `No AI players`
- `Sim turns until 117`

`lobby_lines(settings)` returns only the lines typed into the lobby (timer, map, roads, AI). A fact that is not stated gives no line.

### 5. Where the lines go

- `/info`: after the difficulty and roll lines of `template_info`. For each setting, the value most phases use is given once, and a phase that differs gets one more line `Final: XL+U`, reusing the same most-common logic as the roll lines.
- Rules at the start of a match with a named template: `rules_announcement` receives the lines and adds them right after "The template: X", one message each like the other rules.
- A decided game: `_start_hint` writes "Game 1 is Jebus Cross. Start its trade with /trade start." as it does, as the last line of the message, under the lines that say what is stated about the template.
- Lobby settings: the lobby lines under the title.

`Situation` gets a `settings(template)` method beside `roll_rules(template)`, so the thread messages use the settings of the match's own phase.

Mode view (`/info <mode>`) is unchanged: it lists templates, not their settings.

### 6. Description and additional rules are free text, checked for length only

`description` and `additional_rules` are optional strings of 1 to 1000 characters (`check_text` in `lobby_values.py`). In the catalogue a template may have both. In the format file the tournament may have both at the top level, and `additional_rules` is also a template setting: it is written in the same `settings` objects as the other template settings (a template in the list, or in a phase's pool) and inherited like them, the most specific replacing the one before, starting from the catalogue's `additional_rules` of the template. `Settings` gets an `additional_rules` field and the template's `description` next to `mirror` and where to get it. A tournament may also play another version of a template than the one in HotA: `download` is a template setting too (not a tournament-wide one), and when it is chosen the template stops being built in. The tournament-level `additional_rules` are not inherited by templates: they describe the tournament and are shown by `/info <mode>`.

Display:
- `/info <mode>`: the tournament's description and rules, as lines.
- `/info <mode> <template>`: the template's description, then its rules, giving the value most phases use and a line per phase that differs, as for the other settings.
- The thread: when `post_opening` opens a trade for the first time (`kind == "start"`), it posts `Additional rules: <text>` as a message of its own after the opening record, if the template has rules in the match's phase. A reopened trade does not post it again. The rules are not part of the announcement of a decided game: they are shown when the trade starts, which for a named template is at the start of the match.

*Alternative:* add the rules to every announcement. Rejected: the announcements already carry the settings, and the rules can be long, so they are shown once, where players start the game.

## Risks / Trade-offs

- **Wrong data is worse than none.** Nothing is guessed: a fact that is not stated says nothing, and the shipped data is only filled by the maintainers.
- **A tournament cannot choose what a template does not list as allowed.** This is deliberate (nothing to check against), at the price of completing the template data before a tournament can use the setting.
- **A link that stops working.** The bot cannot know; the link is only shown. Fixing it is a one-line data change.
- **The meaning of a simultaneous-turns date.** Whether the day itself is still simultaneous is an open question in the spec; the wording "until" does not say.
