# rules

The rules of the pre-game, written as plain Python functions. **Nothing in this folder imports `discord`.** Functions take plain values (ids, numbers, text) and return plain values or raise an error whose message is meant for the player.

Why separate: plain functions are easy to test (see [`../../tests/`](../../tests/)) and easy to read without knowing Discord. The Discord code in [`../discord_commands/`](../discord_commands/) calls these functions and shows the result.

| File | What it decides |
|---|---|
| `start.py` | Whether a match can be started, for now: the opponent must be another human |

If a function seems to need a Discord object (a member, a channel), pass in just the plain values it needs, for example `member.id` and `member.bot`.
