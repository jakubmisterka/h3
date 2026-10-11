# discord_commands

The Discord-facing part of the bot: one file per group of slash commands. The `discord_` in the name is a reminder that this is the code that talks to Discord, as opposed to [`../rules/`](../rules/), which holds the tournament logic. (Discord does not require any particular folder names; these are our choice.)

A command here only does the Discord work: read what the player typed, call a plain function from [`../rules/`](../rules/), and send the reply (or create the thread). **No game rules live here.** If you are writing an `if` about how the tournament works, it belongs in `rules/`.

Why separate: code that talks to Discord cannot be tested without Discord. Keeping it thin means the rules can be tested quickly with pytest, and a bug in a rule is found in a test instead of in front of players.

| File | Commands |
|---|---|
| `match.py` | `/match start`, `/match status` |
| `thread_log.py` | Posts each step as one message that starts with a tag like `[#3 ms]`, and reads those messages back into records (the bot keeps no database; the thread is the memory) |
| `permissions.py` | Which Discord permissions the bot needs for each action, and a check that names the missing ones (so players get a clear message, not a crash) |

A command file exposes a `group` (or single commands) that [`../bot.py`](../bot.py) registers.
