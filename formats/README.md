# formats

The tournament formats the bot can run. Each `.json` file here (except `schema.json`) is one format: the rules of the pre-game phase of one tournament or ranked mode. Contributors add a format by adding a file, with no code change.

| File | What it is |
|---|---|
| `el-classico.json` | A format made for development, to be replaced by real tournaments: a best-of-1 with three templates, where A bans one, B bans one, and the template that is left is played. The smallest working example, a good file to copy. |
| `schema.json` | Describes the shape a format file must have: which fields exist, which are required, which values are allowed. Every field has a `description` in it. |

A schema can only check the shape. Rules that compare values (for example "the pool has as many templates as the sequence has steps", or "this template exists in [`../data/templates.json`](../data/templates.json)") are checked by the bot's code and the tests.

This folder will get a full guide for contributors, with an example, once the first format is in.
