"""The /match commands."""

import discord
from discord import app_commands

from rules.start import StartError, check_opponent

# Players are often slow, so keep the thread open for a week before Discord archives it.
THREAD_ARCHIVE_MINUTES = 10080

group = app_commands.Group(name="match", description="Pre-game for a match")


@group.command(name="start", description="Start a match against an opponent")
@app_commands.describe(opponent="The player you are playing against")
async def start(interaction: discord.Interaction, opponent: discord.Member) -> None:
    starter = interaction.user
    channel = interaction.channel

    try:
        check_opponent(starter.id, opponent.id, opponent.bot)
    except StartError as e:
        await interaction.response.send_message(str(e), ephemeral=True)
        return
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "Start a match in a normal text channel, not inside a thread.", ephemeral=True
        )
        return

    # The thread hangs off a message, so first post the message that announces the match.
    await interaction.response.send_message(f"Match: {starter.mention} vs {opponent.mention}")
    announcement = await interaction.original_response()
    thread = await announcement.create_thread(
        name=f"{starter.display_name} vs {opponent.display_name}"[:100],
        auto_archive_duration=THREAD_ARCHIVE_MINUTES,
    )
    await thread.send(f"{starter.mention} {opponent.mention} this is your match thread.")
