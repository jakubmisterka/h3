# rules

The rules of the pre-game, written as plain Python functions. **Nothing in this folder imports `discord`.** Functions take plain values (ids, numbers, text) and return plain values or raise an error whose message is meant for the player.

Why separate: plain functions are easy to test (see [`../../tests/`](../../tests/)) and easy to read without knowing Discord. The Discord code in [`../discord_commands/`](../discord_commands/) calls these functions and shows the result.

| File | What it decides |
|---|---|
| `catalogue.py` | Loads the lists of towns and templates from [`../../data/`](../../data/) and finds an entry by id or name |
| `formats.py` | Loads a tournament format file from [`../../formats/`](../../formats/), checks its shape against the schema and then the rules that compare values, and reports every problem in plain words |
| `info.py` | The text of the `/info` replies (a mode, or a template in a mode), the lines they are built from, and the autocomplete choices. Plain text in, plain text out |
| `registry.py` | Loads the towns, templates and formats together when the bot starts, and reports every problem in every file at once. Also answers which modes a match can be started in, and finds a mode by id or name |
| `difficulty.py` | What a template's difficulty means: the gold each player starts with (80% to 200%) and which steps the trade has |
| `roll_rules.py` | The roll rules (cost of a roll, rolls per player, bans per roll) that apply to one template in one phase, stacking the tournament, template and phase settings on top of the defaults |
| `start.py` | Whether a match can be started: the opponent is another human, the phase and template are valid. The coinflip, the rules messages posted at the start, and the choices offered while typing |
| `ledger.py` | The gold of the two players in one game's trade: the starting gold plus the payments so far, every payment going to the opponent, refused when the payer cannot afford it |
| `trade.py` | The trade of a game: draws the town pair, checks rolls (who may roll, bans, the new pair) and the town and color bid reports, rebuilds the trades of a match from its records (one open at a time, the rest closed as incomplete or finished), finds the game a player means, and words what the thread says |
| `situation.py` | Where a match stands, from the records of its thread: the match, its bans and picks, its games and its trades, each checked. The overview text of `/match status` |
| `selection.py` | Template Selection: whose step is next, whether a ban or pick is allowed, what is left in the pool, and the games in play order once the bans and picks are done |

If a function seems to need a Discord object (a member, a channel), pass in just the plain values it needs, for example `member.id` and `member.bot`.
