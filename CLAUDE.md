# h3

Discord bot for the Heroes of Might and Magic III (Horn of the Abyss) competitive community (Python, discord.py). It runs the 1v1 pre-game flow in a thread per match: `/match start`, `/ban`, `/pick`, `/trade ...`, `/match undo` and `/match status`, plus `/info` for the tournament modes. Features are specified with OpenSpec in `openspec/`.

## Mission

HotA tournament games last 6h+, yet players still burn lobby time on the same pre-game ritual: finding the tournament rules, the template list and the timers, a coinflip for who bans first, bans, rolling two towns each, and trading for towns. None of this needs the game. **This bot runs that whole phase in Discord**, so when players enter the lobby they only read off the settings and start.

- Scope: tournaments organised by h3.gg only. All servers choose from the same catalogue of formats.
- Built so far (change `add-1v1-pregame-flow`): start a match, coinflip, template bans and picks, the trade of each game (town roll, town bid, color bid), undo with both players' consent, and the final lobby settings.
- Tournament formats are **JSON rule-set files in the repo**. Contributors add formats by pull request. Finished tournaments are archived, not deleted.
- Domain reference: https://heroes.thelazy.net (wiki) and h3.gg rules. If a rule is unclear, ask the user or record an open question; never invent tournament rules.
- This repo is meant to be shared: keep code and specs readable for newcomers.

## Workflow (OpenSpec, spec-driven)

Requirements come before code. Specs live in `openspec/specs/`, active work in `openspec/changes/<name>/` (proposal, specs, design, tasks), finished work in `openspec/changes/archive/`.

1. `/opsx:explore`: think through a problem.
2. `/opsx:propose <name>`: create the change artifacts.
3. `/opsx:apply`: implement the tasks.
4. `/opsx:archive`: merge the change into the specs.

Project context and artifact rules are in [openspec/config.yaml](openspec/config.yaml). Do not implement features that have no spec. Work in small explained steps: a milestone is explained first, built in small pieces with tests, and ends with a check the user does in the dev Discord server.

## Secrets: never touch these

- `.env.dev` and `.env.prod` hold Discord bot tokens. **Do not read, print, edit, grep, or copy them**, and don't ask the user to paste tokens into chat.
- `.env.example` is the template: read it to learn the variable names. Ask the user to edit the real files themselves.
- Enforced in [.claude/settings.json](.claude/settings.json): deny rules plus a `PreToolUse` hook ([.claude/hooks/block_secrets.py](.claude/hooks/block_secrets.py)) that blocks Read/Edit/Write/Grep/Glob/Bash/PowerShell calls naming any `.env*` file except `.env.example`. It is best-effort, so don't try to work around it.
- Never log the token or include it in error messages. Config is loaded in [src/config.py](src/config.py).

## Layout

- `src/bot.py`: bot client, loads the data files at start-up (and stops with every problem listed if one is invalid), registers the commands, entry point.
- `src/config.py`: loads `APP_ENV` (`dev`|`prod`, default `dev`), then `.env.<env>`; real environment variables win over the file.
- `src/state.py`: the records a match is made of (`[#n code]` tags), reading them back, and `effective_records` (what still counts after undos). `src/locks.py`: one lock per match thread.
- `src/discord_commands/`: thin Discord handlers, one file per group of commands: `match.py` (`/match start|status|undo`), `selection.py` (`/ban`, `/pick`), `trade.py` (`/trade start|report|roll|skip-roll`), `info.py` (`/info`). Helpers: `guard.py` (the check every match command goes through), `thread_log.py` (posting and reading records), `next_steps.py` (every command ends by posting what comes next), `permissions.py`.
- `src/rules/`: plain, tested rule logic with no Discord imports, and the wording the bot says (in a marked block near the top of each module). `catalogue.py` (towns and templates), `formats.py` (format files and their validation), `registry.py` (loads everything), `difficulty.py`, `roll_rules.py`, `lobby_values.py` (timer, map size and the like), `template_settings.py` and `template_facts.py` (what is played on a template, and how it is worded), `ledger.py` (the gold), `start.py`, `selection.py` (bans and picks), `trade.py`, `undo.py`, `situation.py` (where a match stands, `/match status`, and `next_steps`), `info.py`.
- `formats/`: tournament formats as JSON, plus `schema.json` and a [README](formats/README.md) for contributors. `data/`: the town and template catalogues.
- `tests/`: pytest. Every JSON file in `formats/` and `data/` is checked there, so a bad contribution fails the tests.
- `pyproject.toml` / `poetry.lock`: dependencies (Poetry, `package-mode = false`, venv in `.venv`).

## Commands

```powershell
poetry install                                  # set up .venv from poetry.lock
$env:APP_ENV = "dev"; poetry run python src/bot.py
poetry run pytest                               # all tests, including the format and data files
openspec validate <change> --strict             # check a change's artifacts
poetry add <pkg>                                # add dependency (updates lock)
poetry add --group dev <pkg>                    # dev-only dependency
```

Poetry lives in pipx: if `poetry` isn't on PATH, use `C:\Users\User\.local\bin\poetry.exe`.

## Conventions

- **Never `cd` away from the repo root** in a Bash/PowerShell call (use absolute paths). The secrets hook runs `python .claude/hooks/block_secrets.py` relative to the working directory, and from anywhere else it fails and blocks every tool call.
- Two Discord applications: dev (`h3-trade-DEV`, synced instantly to `TEST_GUILD_ID`) and prod (`h3-trade`, global sync). Same code, different token.
- discord.py is async: never block the event loop (use async DB/HTTP libraries or `asyncio.to_thread`).
- Slash commands only; avoid the privileged Message Content intent.
- Permissions the bot needs in the channels where matches start (checked in `src/discord_commands/permissions.py`, so a missing one is reported by name): View Channel, Send Messages, Create Public Threads (public threads), Create Private Threads (private threads), Send Messages in Threads, Read Message History (to read the match records back). Discord treats public and private threads as separate permissions.
- **No database.** A match lives in the bot's own thread messages: each step is one message starting with a tag like `[#7 tb g1]` (record number, type code, optional game). The bot reads the thread back to know where the match stands, and refuses to guess when a message is missing.
- Keep Discord-facing code thin and put logic and wording in plain functions in `rules/` so they can be unit-tested with pytest.
- Discord limits: an option or command description is at most 100 characters (checked by a test), a message at most 2000, and an autocomplete must answer within 3 seconds (suggestions read the thread through a short cache in `thread_log.py`).
- Tests must not depend on real tournaments or on `data/` ids: they use made-up fixtures in `tests/conftest.py`. Only `tests/test_shipped_files.py` checks the real files. Every new folder gets a `README.md` saying what it is for.
- Use the Heroes III word "town" (not "faction"), and show templates by their display name.
- Discord IDs are 64-bit snowflakes. There is no database today; if one is added, store them as `BIGINT` and key per-server data by `guild_id`.
- Commit `poetry.lock`. Upgrade dependencies on a branch and test on the dev bot before merging.
- Windows/PowerShell environment. Files are written UTF-8 without BOM (a BOM breaks `pyproject.toml`).
