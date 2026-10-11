# rules

The rules of the pre-game, written as plain Python functions. **Nothing in this folder imports `discord`.** Functions take plain values (ids, numbers, text) and return plain values or raise an error whose message is meant for the player.

Why separate: plain functions are easy to test (see [`../../tests/`](../../tests/)) and easy to read without knowing Discord. The Discord code in [`../discord_commands/`](../discord_commands/) calls these functions and shows the result.

| File | What it decides |
|---|---|
| `catalogue.py` | Loads the lists of towns and templates from [`../../data/`](../../data/) and finds an entry by id or name |
| `formats.py` | Loads a tournament format file from [`../../formats/`](../../formats/), checks its shape against the schema and then the rules that compare values, and reports every problem in plain words |
| `registry.py` | Loads the towns, templates and formats together when the bot starts, and reports every problem in every file at once |
| `start.py` | Whether a match can be started, for now: the opponent must be another human |

If a function seems to need a Discord object (a member, a channel), pass in just the plain values it needs, for example `member.id` and `member.bot`.
