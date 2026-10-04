import logging
from pathlib import Path

import discord
from discord import app_commands

from commands import match, selection, trade
from config import load_config
from locks import ThreadLocks
from rules.catalogue import CatalogueError
from rules.formats import FormatError
from rules.registry import Registry, load_registry

log = logging.getLogger("h3bot")

REPO_ROOT = Path(__file__).resolve().parent.parent


class H3Bot(discord.Client):
    def __init__(self, test_guild_id: int | None, registry: Registry):
        # Slash commands need no privileged intents.
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.test_guild_id = test_guild_id
        self.registry = registry
        self.locks = ThreadLocks()
        self.tree.add_command(match.group)
        self.tree.add_command(selection.ban)
        self.tree.add_command(selection.pick)
        self.tree.add_command(trade.group)

    async def setup_hook(self) -> None:
        if self.test_guild_id:
            # Guild-scoped sync appears instantly; global sync can take a while.
            guild = discord.Object(id=self.test_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()
    try:
        registry = load_registry(REPO_ROOT)
    except (FormatError, CatalogueError) as e:
        raise SystemExit(f"Cannot start, a data file is invalid: {e}")
    bot = H3Bot(cfg.test_guild_id if cfg.env == "dev" else None, registry)
    bot.run(cfg.token, log_handler=None)


if __name__ == "__main__":
    main()
