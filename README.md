# h3

Features for h3 community: a Discord bot that moves the pre-game of a Heroes of Might and Magic III (Horn of the Abyss) tournament match out of the game lobby and into Discord. Work in progress: today `/match start` opens a thread for a match. The plan is in `CLAUDE.md` and `openspec/`.

## One-time Discord setup (do twice: `h3-trade-DEV` and `h3-trade`)

1. https://discord.com/developers/applications -> New Application.
2. Bot tab -> Reset Token -> copy it. No privileged intents are needed.
3. OAuth2 -> URL Generator -> scopes `bot` + `applications.commands`, permissions *View Channel*, *Send Messages*, *Send Messages in Threads*, *Create Public Threads*, *Create Private Threads* and *Read Message History* -> open the URL and add the bot to a server you manage.
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

In Discord, type `/match start`. In dev the commands appear immediately in the test server; in prod, global commands can take a while to propagate after the first start.

The bot first checks the data files (`data/` and `formats/`) and refuses to start if one is not valid, saying which file and what is wrong. This needs no token, so you can use it to check a file you are editing.

## Tests

```powershell
poetry run pytest
```

They need no token and never connect to Discord. They also check every file in `formats/` and `data/`, so a mistake in a contribution fails here. See `tests/README.md`.

## Secrets

`.env.*` files are gitignored. In production prefer real environment variables (systemd `EnvironmentFile`, platform secrets, or a key vault); the bot only reads `DISCORD_TOKEN` from the environment.
