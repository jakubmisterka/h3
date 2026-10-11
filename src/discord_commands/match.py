"""The /match commands."""

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.permissions import PRIVATE_THREAD, PUBLIC_THREAD, missing, missing_message
from discord_commands.thread_log import ThreadLog
from rules.start import StartError, check_opponent
from state import describe_records

# Players are often slow, so keep the thread open for a week before Discord archives it.
THREAD_ARCHIVE_MINUTES = 10080

group = app_commands.Group(name="match", description="Pre-game for a match")


def refused_message(error: discord.Forbidden) -> str:
    """Text for a refusal we did not predict. The permission check below catches the usual causes first."""
    return f"Discord refused to create the thread ({error.text}). Please ask a server admin to check my permissions."


async def post_match_started(thread: discord.Thread, bot_id: int, starter, opponent) -> None:
    """The first message of a match thread (mentioning both players notifies them), then the first record."""
    await ThreadLog(thread, bot_id).post(
        "match_started",
        f"Match started: {starter.mention} vs {opponent.mention}. This is your match thread.",
        p1=starter.id,
        p2=opponent.id,
    )


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
            await post_match_started(thread, interaction.client.user.id, starter, opponent)
        except discord.Forbidden as e:
            await interaction.followup.send(refused_message(e))
    else:
        # A public thread hangs off a message, so first post the message that announces the match.
        await interaction.response.send_message(f"Match: {starter.mention} vs {opponent.mention}")
        try:
            announcement = await interaction.original_response()
            thread = await announcement.create_thread(name=title, auto_archive_duration=THREAD_ARCHIVE_MINUTES)
            await post_match_started(thread, interaction.client.user.id, starter, opponent)
        except discord.Forbidden as e:
            # Do not leave an announcement without a thread behind: replace its text with the explanation.
            await interaction.edit_original_response(content=refused_message(e))


@group.command(name="status", description="Show what the bot has recorded in this match thread")
async def status(interaction: discord.Interaction) -> None:
    records = await guarded_records(interaction)  # replies to the user itself when it says no
    if records is None:
        return
    await interaction.followup.send(describe_records(records))
