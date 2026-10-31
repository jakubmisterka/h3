# docs

User documentation of the bot, for players and tournament organisers.

| File | What it is |
|---|---|
| [`instrukcja.md`](instrukcja.md) | The user guide, in Polish: what the bot does, every command, a match step by step with real bot messages, the kinds of trade, undo and `/info`, the tournaments the bot knows, and where contributors go next |
| [`obrazy/`](obrazy/) | The screenshots the guide refers to (see its README) |

The examples in the guide are real messages of the bot, produced from the shipped data files. When wording or a tournament changes, check that the examples still match (the tests in `tests/` fail on a change in wording, so look at the ones the change touched). Developer documentation is in the READMEs of each folder and in [`../CLAUDE.md`](../CLAUDE.md).
