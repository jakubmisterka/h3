# Proposal: a link to the tournament's rules

## Why

A format file holds only the parts of a tournament's rules that the bot uses. Players often need the full rules (fair play, deadlines, penalties, restarts), and today the bot gives them no way to find the document. The organisers publish it as a document, so the format can carry its link.

## What the players see

When a match starts, the rules the bot posts include one more line with the link to the tournament's full rules. `/info` for the mode shows the same link under its description. A tournament without a link shows no such line.

```
Format: BO3
Rules: [full tournament rules](<https://docs.google.com/...>)
```

## What changes

- A new optional field of a format, `rules_link`: a link starting with `https://`.
- The rules posted at the start of a match and the `/info` reply for a mode show it.
- The shipped formats of the tournaments that have a published ruleset state it.
- Docs: `formats/README.md`, the Polish guide.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-formats`: a format can state the link to its rules.
- `match-setup`: the rules at the start of a match name the link.
- `mode-info`: the reply for a mode names the link.

## Out of scope

- A link per phase or per template (the rules are one document for the tournament).
- Checking that the link works, or reading the document.

## Impact

`src/rules/formats.py`, `src/rules/start.py`, `src/rules/info.py`, `src/discord_commands/match.py`, `formats/schema.json`, the format files, the docs, and tests.
