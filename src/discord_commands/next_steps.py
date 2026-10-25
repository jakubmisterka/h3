"""Saying what the players can do next. Every command ends with this, so the thread always reads the same way."""

import discord

from rules.selection import SelectionError
from rules.situation import next_steps, situation_of, unreadable
from rules.trade import TradeError
from state import MatchError, Record, RecordError


async def post_next_steps(thread: discord.Thread, registry, records: list[Record]) -> None:
    """Post what comes next, worked out from the records of the thread (including the one just posted)."""
    try:
        s = situation_of(registry, records)
    except (MatchError, RecordError, SelectionError, TradeError) as e:
        await thread.send(unreadable(e))
        return
    for message in next_steps(s, registry.templates, registry.towns):
        await thread.send(message)
