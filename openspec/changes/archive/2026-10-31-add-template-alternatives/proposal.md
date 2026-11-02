# Proposal: alternative versions of a template

## Why

Tournament rules sometimes say: "if both players agree, you may play `h3dm1_nc` instead of `h3dm1`". The alternative is the same setting with a different generation (zone sizes, towns forced into zones, banned heroes or artifacts). It usually is not built into HotA, so players need to be told that it exists and where to download it. Today a tournament can only state that in its free-text rules, where nobody reads it when the game starts.

## What the players see

When the trade of a game starts, the lines about the template include one more:

```
By agreement the template can be changed to `h3dm1_nc` ([download](<https://...>)). To learn more use /info
```

A match started with a named template shows it in the same place. `/info` for the mode and the template shows the alternatives too, with their download links. Nothing else changes: the match, the starting gold and the lobby settings stay those of the template the match was started with. The bot does not record which version was played.

## What changes

- A new per-template tournament setting `alternatives`: a list of template ids, stated in a template's `settings` in the tournament's list or in a phase's pool, like the timer.
- Every alternative must be a template of the catalogue (`data/templates.json`) and must be either built into HotA or have a download link, so the message is useful.
- The announcement lines for a template (`/trade start` and the start of a match with a named template) and the `/info` reply for a template name the alternatives.
- Docs: `formats/README.md`, `data/README.md` and the format schema.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-formats`: a tournament can state alternatives for a template, and they are checked.
- `match-setup`: the lines about a template at the start of a trade name its alternatives.
- `mode-info`: the reply for a template names its alternatives.

## Out of scope

- Recording which version the players chose, or letting them choose with a command.
- Alternatives with their own difficulty, timer or other settings. The match keeps the settings of the main template.
- Alternatives set in the catalogue for every tournament; the setting is a tournament's rule.

## Impact

`src/rules/template_settings.py`, `src/rules/template_facts.py`, `src/rules/formats.py` (validation), `src/rules/info.py`, `formats/schema.json`, the READMEs, `data/templates.json` (the alternatives themselves, added by the maintainers), and tests.
