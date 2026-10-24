"""The /ban and /pick commands: Template Selection, one step at a time."""

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.thread_log import ThreadLog
from locks import thread_lock
from rules.info import AUTOCOMPLETE_LIMIT, find_phase
from rules.selection import (
    Action,
    SelectionError,
    after_a_step,
    check_action,
    choose_available,
    next_step,
    remaining,
    replay,
)
from state import MatchError, RecordError, rebuild


PAST = {"ban": "banned", "pick": "picked"}


def situation(registry, records):
    """The match, its phase and the actions so far, from the records. Raises when the thread cannot be trusted."""
    match = rebuild(records)
    fmt = registry.find_format(match.mode)
    phase = find_phase(fmt, match.phase) if fmt else None
    if phase is None:
        raise MatchError(f"This match is in {match.mode!r}, phase {match.phase!r}, which I no longer have.")
    if phase.agreed:
        raise MatchError("In this match the players agreed on the template, so there are no bans or picks.")
    actions = replay(phase.steps, phase.pool_ids, match.a, match.b, match.taken)
    return match, phase, actions


async def post_next(thread: discord.Thread, registry, phase, a_mention: str, b_mention: str, actions) -> None:
    """The plain messages after the coinflip and after each step: the pool, then what comes next."""
    mentions = {"A": a_mention, "B": b_mention}
    for message in after_a_step(phase.steps, phase.pool_ids, actions, mentions, registry.templates):
        await thread.send(message)


async def take_step(interaction: discord.Interaction, do: str, template_text: str) -> None:
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await guarded_records(interaction)  # tells the player to use the match thread
        return

    registry = interaction.client.registry
    # One command at a time per thread, from reading the thread to posting the record (see locks.py).
    async with thread_lock(thread.id):
        records = await guarded_records(interaction)  # replies to the user itself when it says no
        if records is None:
            return
        try:
            match, phase, actions = situation(registry, records)
            who = "A" if interaction.user.id == match.a else "B"
            check_action(phase.steps, actions, who, do)
            template_id = choose_available(template_text, remaining(phase.pool_ids, actions), registry.templates)
        except (MatchError, RecordError, SelectionError) as e:
            await interaction.followup.send(str(e))
            return

        name = registry.templates.find(template_id).name
        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        await log.post(
            do,
            f"{interaction.user.mention} {PAST[do]} **{name}** (`{template_id}`)",
            player=interaction.user.id,
            template=template_id,
        )
        actions.append(Action(who, do, template_id))
        await post_next(thread, registry, phase, f"<@{match.a}>", f"<@{match.b}>", actions)
        await interaction.followup.send(f"You {PAST[do]} {name}.")


async def remaining_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """The templates still available, while a player is typing. Any problem just means no suggestions."""
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        return []
    registry = interaction.client.registry
    try:
        records = await ThreadLog(thread, interaction.client.user.id).read()
        _, phase, actions = situation(registry, records)
    except (MatchError, RecordError, SelectionError, discord.HTTPException):
        return []
    wanted = current.strip().lower()
    entries = [registry.templates.find(template) for template in remaining(phase.pool_ids, actions)]
    return [
        app_commands.Choice(name=entry.name, value=entry.id)
        for entry in entries
        if wanted in entry.name.lower() or wanted in entry.id.lower()
    ][:AUTOCOMPLETE_LIMIT]


@app_commands.command(name="ban", description="Ban a template when it is your step")
@app_commands.describe(template="The template to ban")
async def ban(interaction: discord.Interaction, template: str) -> None:
    await take_step(interaction, "ban", template)


@app_commands.command(name="pick", description="Pick a template when it is your step")
@app_commands.describe(template="The template to pick")
async def pick(interaction: discord.Interaction, template: str) -> None:
    await take_step(interaction, "pick", template)


ban.autocomplete("template")(remaining_options)
pick.autocomplete("template")(remaining_options)
