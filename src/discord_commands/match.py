"""The /match commands."""

import discord
from discord import app_commands

from discord_commands.permissions import PRIVATE_THREAD, PUBLIC_THREAD, missing, missing_message
from rules.start import StartError, check_opponent

# Players are often slow, so keep the thread open for a week before Discord archives it.
THREAD_ARCHIVE_MINUTES = 10080

group = app_commands.Group(name="match", description="Pre-game for a match")


def refused_message(error: discord.Forbidden) -> str:
    """Text for a refusal we did not predict. The permission check below catches the usual causes first."""
    return f"Discord refused to create the thread ({error.text}). Please ask a server admin to check my permissions."


@group.command(name="start", description="Start a match against an opponent")
@app_commands.describe(
    opponent="The player you are playing against",
    private="Temporary: True opens a private thread only the two players can see (default: a public thread)",
)
async def start(interaction: discord.Interaction, opponent: discord.Member, private: bool = False) -> None:
    starter = interaction.user
    channel = interaction.channel
    title = f"{starter.display_name} vs {opponent.display_name}"[:100]

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

    # Check the bot's permissions here first, so nothing is posted before we find out it cannot finish.
    lacking = missing(interaction.app_permissions, PRIVATE_THREAD if private else PUBLIC_THREAD)
    if lacking:
        await interaction.response.send_message(missing_message(lacking), ephemeral=True)
        return

    if private:
        # A private thread stands alone in the channel: create it, then add both players by hand.
        # Creating it can take longer than the 3 seconds Discord allows for a first reply, so defer.
        # The reply is ephemeral (only the player who ran the command sees it); the opponent is
        # told by being added to the thread and mentioned in it.
        await interaction.response.defer(ephemeral=True)
        try:
            thread = await channel.create_thread(
                name=title,
                type=discord.ChannelType.private_thread,
                invitable=False,  # players cannot add other people
                auto_archive_duration=THREAD_ARCHIVE_MINUTES,
            )
            await thread.add_user(starter)
            await thread.add_user(opponent)
            await interaction.followup.send(f"Your private match thread with {opponent.mention}: {thread.mention}")
            await thread.send(f"{starter.mention} {opponent.mention} this is your match thread.")
        except discord.Forbidden as e:
            await interaction.followup.send(refused_message(e))
    else:
        # A public thread hangs off a message, so first post the message that announces the match.
        await interaction.response.send_message(f"Match: {starter.mention} vs {opponent.mention}")
        try:
            announcement = await interaction.original_response()
            thread = await announcement.create_thread(name=title, auto_archive_duration=THREAD_ARCHIVE_MINUTES)
            await thread.send(f"{starter.mention} {opponent.mention} this is your match thread.")
        except discord.Forbidden as e:
            # Do not leave an announcement without a thread behind: replace its text with the explanation.
            await interaction.edit_original_response(content=refused_message(e))
