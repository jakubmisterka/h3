import logging
from pathlib import Path

import discord
from discord import app_commands

from config import load_config
from discord_commands import match
from discord_commands.info import info as info_command
from discord_commands.selection import ban, pick
from rules.registry import Registry, RegistryError, load_registry

log = logging.getLogger("h3bot")

REPO_ROOT = Path(__file__).resolve().parent.parent


class H3Bot(discord.Client):
    def __init__(self, test_guild_id: int | None, registry: Registry):
        # Slash commands need no privileged intents.
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.test_guild_id = test_guild_id
        self.registry = registry  # the towns, templates and formats, checked once at start-up
        self.tree.add_command(match.group)
        self.tree.add_command(info_command)
        self.tree.add_command(ban)
        self.tree.add_command(pick)

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


def load_data_or_exit(root: Path = REPO_ROOT) -> Registry:
    """Load the data files, or stop with a message that names every problem and the file it is in."""
    try:
        registry = load_registry(root)
        log.info("Data loaded: %s", registry.summary())
        return registry
    except RegistryError as e:
        problems = "\n".join(f"  - {problem}" for problem in e.problems)
        raise SystemExit(f"Cannot start: a data file is not valid.\n{problems}") from e


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    registry = load_data_or_exit()  # first: a contributor checking a file needs no token for this
    cfg = load_config()
    bot = H3Bot(cfg.test_guild_id if cfg.env == "dev" else None, registry)
    bot.run(cfg.token, log_handler=None)


if __name__ == "__main__":
    main()
