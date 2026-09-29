# h3

Features for h3 community. Currently a Discord bot with a single `/hello` slash command.

## One-time Discord setup (do twice: `HelloBot-Dev` and `HelloBot`)

1. https://discord.com/developers/applications -> New Application.
2. Bot tab -> Reset Token -> copy it. No privileged intents are needed.
3. OAuth2 -> URL Generator -> scopes `bot` + `applications.commands`, permission *Send Messages* -> open the URL and add the bot to a server you manage.
   Add the dev bot to a private test server and the prod bot to real servers.
4. Dev only: enable Developer Mode in Discord (Settings -> Advanced), right-click your test server -> Copy Server ID.

## Local setup

Dependencies are managed with [Poetry](https://python-poetry.org/). Install it once with pipx:

```powershell
python -m pip install --user pipx
python -m pipx install poetry
python -m pipx ensurepath       # then open a new terminal
```

Then, in the repo:

```powershell
poetry install                  # creates .venv and installs from poetry.lock
copy .env.example .env.dev      # fill in dev token + TEST_GUILD_ID
copy .env.example .env.prod     # fill in prod token (leave TEST_GUILD_ID empty)
```

Common Poetry commands: `poetry add <pkg>` (add a dependency), `poetry add --group dev <pkg>` (dev-only, e.g. pytest), `poetry remove <pkg>`, `poetry update` (upgrade within constraints), `poetry run <cmd>` (run inside the environment).

## Run

```powershell
$env:APP_ENV = "dev"            # or "prod"; defaults to dev
poetry run python src/bot.py
```

In Discord, type `/hello`. In dev the command appears immediately in the test server; in prod, global commands can take a while to propagate after the first start.

## Secrets

`.env.*` files are gitignored. In production prefer real environment variables (systemd `EnvironmentFile`, platform secrets, or a key vault); the bot only reads `DISCORD_TOKEN` from the environment.
