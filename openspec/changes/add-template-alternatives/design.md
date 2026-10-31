# Design

## Context

A template's settings (timer, roads, sim turns, trade and the like) are stacked from the catalogue, the tournament, the template in the tournament's list and the template in a phase's pool (`template_settings.effective_settings`). The lines posted about a template come from `template_facts.announcement_lines`, which `/trade start` and the start of a match with a named template use. `/info` for a template reads the same settings. A template that has to be downloaded states it in the catalogue (`download`), and one that comes with HotA states `built_in`.

## Goals / Non-Goals

**Goals:**
- Players are told, when a trade starts and in `/info`, that an alternative exists and where to get it.
- A typo in an alternative is caught when the format is loaded.

**Non-Goals:**
- Recording which version was played, or any settings of the alternative itself (see the proposal).

## Decisions

**A setting of the tournament, not of the catalogue.** `alternatives` is a list of template ids in a template's `settings` (list or pool), stacked with the others. The same template can have different alternatives in different tournaments, since each tournament states the permission.

**Alternatives are catalogue templates.** They are checked against `data/templates.json`, so a typo fails loading and the alternative's download link or `built_in` comes from its own entry, where the maintainers keep it. Requiring "built in or a link" is what makes the line useful. An alternative does not have to be in the tournament's template list: it is not played through the bans and picks.

**One line, after the facts.** `announcement_lines` adds the line after the trade rule (and before the hint to `/info`, which stays last when it is asked for). It names each alternative by its display name in code, with its link: ``By agreement the template can be changed to `h3dm1_nc` ([download](<url>))``; several are joined by "or". An alternative built into HotA has no link. The hint to `/info`, which closes the lines, already says how to learn more.

**`/info`.** The template reply shows the alternatives with the usual "differs by phase" treatment of the other settings.

**No match change.** Records, starting gold and the lobby settings are untouched; the match keeps the template it was started with.

## Risks / Trade-offs

- The alternative's own difficulty is not used. This is as asked: alternatives are variations of the same setting. If one ever differs, it needs its own change.
- The line is posted on every trade start for that template, also when the players never use the alternative. That is the point: the permission is easy to miss otherwise.
