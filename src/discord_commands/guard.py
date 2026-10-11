"""The check every match command goes through before it does anything.

A match command may only be used inside a match thread, and only by one of the match's two
players. The bot finds out who the players are by reading the thread's records (see `state.py`).
"""

import discord

from discord_commands.permissions import READ_THREAD, missing, missing_message
from discord_commands.thread_log import ThreadLog
from state import MatchError, Record, RecordError, check_player

NOT_IN_THREAD = "Use this command inside a match thread."


async def guarded_records(interaction: discord.Interaction) -> list[Record] | None:
    """Return the records of the match thread this command was used in, if the user may use it.

    When the answer is no (not in a thread, not a match thread, not one of the players, the bot
    cannot read the thread), the user is told why, privately, and None is returned: the caller
    just stops. When the answer is yes, the interaction is already acknowledged (deferred, and
    only the user sees the reply), so the caller continues with `interaction.followup`.
    """
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message(NOT_IN_THREAD, ephemeral=True)
        return None

    lacking = missing(interaction.app_permissions, READ_THREAD)
    if lacking:
        await interaction.response.send_message(missing_message(lacking), ephemeral=True)
        return None

    # Reading a long thread can take a moment, so acknowledge first.
    await interaction.response.defer(ephemeral=True)
    try:
        records = await ThreadLog(thread, interaction.client.user.id).read()
        check_player(records, interaction.user.id)
    except RecordError as e:
        await interaction.followup.send(f"I can't read this thread: {e}")
        return None
    except MatchError as e:
        await interaction.followup.send(str(e))
        return None
    return records
