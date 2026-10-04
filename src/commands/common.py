"""Shared guard for commands that act on an existing match."""

from contextlib import asynccontextmanager

import discord

from rules import trade
from rules.errors import UserError
from rules.start import check_player
from state import Match, StateError, fold
from threads import ThreadLog

NOT_IN_THREAD = "Use this command inside the match thread."


def mentions(user_ids) -> str | None:
    return " ".join(f"<@{u}>" for u in user_ids) or None


async def post_action(log: ThreadLog, action: trade.Action) -> None:
    """Post a trade action as an event, notifying the players who have to act next."""
    await log.post(action.type, action.text, ping=mentions(action.ping), **action.data)


async def start_trade_of(match, number: int, log: ThreadLog, client) -> Match:
    """Start the trade of a game (the bot draws the pair or toss) and return the updated match."""
    action = trade.start_trade(match, number, client.registry.factions)
    await post_action(log, action)
    return trade.after(match, number, action.type, action.data)


@asynccontextmanager
async def match_session(interaction: discord.Interaction):
    """Run a command on the match of the thread it was used in.

    Yields (match, log) while holding that thread's lock, or None after telling the
    player what is wrong (not a thread, not a match thread, not one of the players).
    A UserError raised inside the block is shown to the player too. When the block
    ends normally the "thinking" reply is removed, because the result was posted
    in the thread.
    """
    client = interaction.client
    channel = interaction.channel
    await interaction.response.defer(ephemeral=True)

    if not isinstance(channel, discord.Thread):
        await interaction.followup.send(NOT_IN_THREAD, ephemeral=True)
        yield None
        return

    async with client.locks.hold(channel.id):
        log = ThreadLog(channel, client.user.id)
        try:
            match = fold(await log.read(), client.registry.formats)
            check_player(match.players, interaction.user.id)
        except StateError as e:
            await interaction.followup.send(f"I can't use this thread: {e}.", ephemeral=True)
            yield None
            return
        except UserError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            yield None
            return

        try:
            yield match, log
        except UserError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

    await interaction.delete_original_response()
