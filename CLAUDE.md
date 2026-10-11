# h3

Discord bot for the Heroes of Might and Magic III (Horn of the Abyss) competitive community (Python, discord.py). Currently a single `/hello` slash command; the real features are being specified with OpenSpec.

## Mission

HotA tournament games last 6h+, yet players still burn lobby time on the same pre-game ritual: finding the tournament rules, the template list and the timers, a coinflip for who bans first, bans, rolling two towns each, and trading for towns. None of this needs the game. **This bot runs that whole phase in Discord**, so when players enter the lobby they only read off the settings and start.

- Scope: tournaments organised by h3.gg only. All servers choose from the same catalogue of formats.
- First milestone: the 1v1 pre-game flow end to end (start match, coinflip, bans, town roll, trading, final lobby-settings summary).
- Tournament formats are **JSON rule-set files in the repo**. Contributors add formats by pull request. Finished tournaments are archived, not deleted.
- Domain reference: https://heroes.thelazy.net (wiki) and h3.gg rules. If a rule is unclear, ask the user or record an open question; never invent tournament rules.
- This repo is meant to be shared: keep code and specs readable for newcomers.

## Workflow (OpenSpec, spec-driven)

Requirements come before code. Specs live in `openspec/specs/`, active work in `openspec/changes/<name>/` (proposal, specs, design, tasks), finished work in `openspec/changes/archive/`.

1. `/opsx:explore`: think through a problem (used for the trading-system discussion).
2. `/opsx:propose <name>`: create the change artifacts.
3. `/opsx:apply`: implement the tasks.
4. `/opsx:archive`: merge the change into the specs.

Project context and artifact rules are in [openspec/config.yaml](openspec/config.yaml). Do not implement features that have no spec.

## Secrets: never touch these

- `.env.dev` and `.env.prod` hold Discord bot tokens. **Do not read, print, edit, grep, or copy them**, and don't ask the user to paste tokens into chat.
- `.env.example` is the template: read it to learn the variable names. Ask the user to edit the real files themselves.
- Enforced in [.claude/settings.json](.claude/settings.json): deny rules plus a `PreToolUse` hook ([.claude/hooks/block_secrets.py](.claude/hooks/block_secrets.py)) that blocks Read/Edit/Write/Grep/Glob/Bash/PowerShell calls naming any `.env*` file except `.env.example`. It is best-effort, so don't try to work around it.
- Never log the token or include it in error messages. Config is loaded in [src/config.py](src/config.py).

## Layout

- `src/bot.py`: bot client, command registration, entry point.
- `src/config.py`: loads `APP_ENV` (`dev`|`prod`, default `dev`), then `.env.<env>`; real environment variables win over the file.
- `pyproject.toml` / `poetry.lock`: dependencies (Poetry, `package-mode = false`, venv in `.venv`).

## Commands

```powershell
poetry install                                  # set up .venv from poetry.lock
$env:APP_ENV = "dev"; poetry run python src/bot.py
poetry add <pkg>                                # add dependency (updates lock)
poetry add --group dev <pkg>                    # dev-only dependency
```

Poetry lives in pipx: if `poetry` isn't on PATH, use `C:\Users\User\.local\bin\poetry.exe`.

## Conventions

- Two Discord applications: dev (`HelloBot-Dev`, synced instantly to `TEST_GUILD_ID`) and prod (global sync). Same code, different token.
- discord.py is async: never block the event loop (use async DB/HTTP libraries or `asyncio.to_thread`).
- Slash commands only; avoid the privileged Message Content intent.
- Keep Discord-facing code thin and put logic in plain functions so it can be unit-tested with pytest.
- Discord IDs are 64-bit snowflakes: store as `BIGINT`, key per-server data by `guild_id`.
- Commit `poetry.lock`. Upgrade dependencies on a branch and test on the dev bot before merging.
- Windows/PowerShell environment. Files are written UTF-8 without BOM (a BOM breaks `pyproject.toml`).
