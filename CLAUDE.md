# h3

Discord bot for the h3 community (Python, discord.py). Currently a single `/hello` slash command.

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
