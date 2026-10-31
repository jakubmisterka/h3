# Design

## Context

A match thread knows its games in one of two ways. With a template named at the start (`ms` record has `Template:`), the match has one game on that template. Otherwise the games are what the bans and picks decided (`known_games`), and the match has `best_of` games. `Situation.has_selection` is true exactly in the second case, and `total_games` is `best_of` if it is true and 1 if not. Several places (the next steps after a trade, `/match status`, `/ban` and `/pick`) branch on `has_selection`.

A fixed phase has neither: no template is named, no steps run, yet there are `best_of` games, all known at the start.

## Goals / Non-Goals

**Goals:**
- A format file can say "every game of this phase is on this template", checked when the file is loaded.
- A match in such a phase plays through all its games with the messages players already know.
- No new record types, and no change to how existing formats behave.

**Non-Goals:**
- Agreed phases with several games, results, and ending a best-of early (see the proposal).

## Decisions

**An explicit `fixed` type, not an implied one.** `template_selection: { "type": "fixed" }` beside `sequence` and `agreed`. A one-template pool that silently skipped the bans would hide a forgotten second template; with the explicit type the file is refused instead. The template is the phase's pool when it has one, otherwise the tournament's list; either must hold exactly one.

**`Phase.fixed` and one place that knows the games.** `Phase` gets a `fixed` flag (next to `agreed`). `situation_of` decides the games: a named template gives `(template,)`, a fixed phase gives `(template,) * best_of`, otherwise the selection does. `Situation` gets a property `selection_runs` (a selection step may still come: not named and not fixed) and `has_selection` keeps its meaning for the places that ask whether bans and picks exist; `total_games` is `len(games)` when the games are known at the start and `best_of` otherwise. The places that branch on `has_selection` for "is there a selection" stay as they are; the two that mean "is there only one game" (`_after_a_finished_trade`, the `/match status` overview) use `total_games` instead.

**The match record does not change.** The `ms` record has `Template:` only when a template was named. A fixed phase names none, so the record reads back the same as for a sequence phase, and the phase decides the games. Naming the fixed template at the start is accepted and also recorded as nothing (the same match), so a name never changes the number of games.

**Starting.** `choose_template` returns `None` for a fixed phase when none is named, accepts the phase's template when named, and refuses any other with the phase's template listed (the same refusal as a template outside the pool). `begin_match` for a fixed phase posts the rules like a match with a named template (the format, then the template facts) and opens the trade of game 1 itself.

**Wording.** The format line is `Format: BO3` (the best-of of the phase). The finished-trade message for a game that is not the last is the existing "Game N is X. Start its trade with /trade start." The last game, once traded, gets the "every game traded" note that sequence phases already have.

**`/info`.** The Template Selection line is replaced by "All N games are played on `X`" for a fixed phase.

## Risks / Trade-offs

- `has_selection` has several readers; changing its meaning would silently change refusals. Keeping it and adding `total_games` from the games keeps the existing behaviour and makes the new case explicit. Tests for each reader (`/ban`, `/pick`, next steps, status, undo) cover it.
- A fixed phase of one game (BO1) behaves like a named template. That is fine and needs no special case.

Open question: how many games a match of the Swiss phase of Sapphire Battlegrounds 3 has; its rules give BO3 only for the knockout. Provisional default: `formats/sapphire-battlegrounds-3.json` has best-of 1 for the Swiss phase, until the organisers say.
