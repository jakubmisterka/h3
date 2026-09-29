import logging

import discord
from discord import app_commands

from config import load_config

log = logging.getLogger("hellobot")


class HelloBot(discord.Client):
    def __init__(self, test_guild_id: int | None):
        # Slash commands need no privileged intents.
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.test_guild_id = test_guild_id

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
    bot = HelloBot(cfg.test_guild_id if cfg.env == "dev" else None)

    @bot.tree.command(name="hello", description="Say hello")
    async def hello(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello World")

    bot.run(cfg.token, log_handler=None)


if __name__ == "__main__":
    main()
