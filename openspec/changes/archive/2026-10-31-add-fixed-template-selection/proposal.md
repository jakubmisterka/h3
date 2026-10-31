# Proposal: a phase that plays every game on one template

## Why

Some tournaments are played on a single template, with matches of several games (for example a BO3 where all three games are on the same template). Today a phase either runs bans and picks, which needs one template per step, or lets the players agree on a template, which makes a match of one game. There is no way to say "every game of this match is on this template", so these tournaments cannot be added to the repo.

## What the players see

In a phase of this kind there is nothing to select. The player who starts the match names no template. The thread says the format (for example `Format: BO3`), what is stated about the template (download link, timer, sim turns, how the trade is run), does the coinflip, and the bot opens the trade of game 1. When the trade of a game is done, the bot says which game is next and how to start its trade, until every game of the best-of has been traded. The ban and pick commands tell the player that this phase has no bans or picks. `/info` for the mode says that every game is played on the template.

## What changes

- A new kind of `template_selection` for a phase: `{ "type": "fixed" }`, with no steps.
- Validation: a fixed phase must have exactly one template, in the tournament's list or in the phase's `pool`.
- Starting a match in a fixed phase needs no template; the bot takes the only one. A match of `best_of` games is played, each on that template.
- The finished-trade message, `/match status` and the undo texts handle several games on a template with no selection.
- `/info` for a mode says that the phase plays every game on its template.
- Docs: `formats/README.md` and the format schema.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-formats`: a phase can choose its templates in a third way (fixed), and a fixed phase must have exactly one template.
- `match-setup`: a match in a fixed phase starts without a named template and has as many games as the best-of.
- `template-selection`: a fixed phase has no bans or picks, and its games are the template repeated.
- `mode-info`: the reply for a fixed phase says every game is on the same template.

## Out of scope

- Playing a best-of with the players agreeing on a template for each game (an `agreed` phase still makes a match of one game; this change does not alter that).
- Tracking game results or ending a best-of early when a player has won the majority of games. The bot only runs the pre-game phase of each game, as it does for every other format.
- Choosing a different template for one game of a fixed phase.

## Impact

`src/rules/formats.py` (the phase and its validation), `src/rules/start.py`, `src/rules/situation.py`, `src/rules/info.py`, `src/rules/selection.py` (the ban and pick refusal), `src/discord_commands/match.py`, `formats/schema.json`, `formats/README.md`, and tests.
