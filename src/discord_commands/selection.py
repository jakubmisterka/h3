"""The /ban and /pick commands: Template Selection, one step at a time."""

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.thread_log import ThreadLog, logger, records_for_autocomplete
from locks import thread_lock
from rules.info import AUTOCOMPLETE_LIMIT
from rules.selection import (
    Action,
    SelectionError,
    after_a_step,
    check_action,
    choose_available,
    known_games,
    remaining,
)
from rules.situation import situation_of
from rules.trade import TradeError
from state import MatchError, RecordError

PAST = {"ban": "banned", "pick": "picked"}
NOT_A_STEP = "In this match the players agreed on the template, so there are no bans or picks."


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
            s = situation_of(registry, records)
            if s.phase.agreed:
                raise MatchError(NOT_A_STEP)
            who = "A" if interaction.user.id == s.match.a else "B"
            check_action(s.phase.steps, s.actions, who, do)
            template_id = choose_available(template_text, remaining(s.phase.pool_ids, s.actions), registry.templates)
        except (MatchError, RecordError, SelectionError, TradeError) as e:
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
        actions = s.actions + [Action(who, do, template_id)]
        await post_next(thread, registry, s.phase, f"<@{s.match.a}>", f"<@{s.match.b}>", actions)

        # A pick (or the last step, for the decider's game) makes a game known: its trade can start right away.
        decided = known_games(s.phase.steps, s.phase.pool_ids, actions)
        for number in range(len(s.games) + 1, len(decided) + 1):
            game_name = registry.templates.find(decided[number - 1]).name
            await thread.send(f"Game {number} is {game_name}. Start its trade with /trade start.")
        await interaction.followup.send(f"You {PAST[do]} {name}.")


async def remaining_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """The templates still available, while a player is typing. Any problem just means no suggestions."""
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        return []
    registry = interaction.client.registry
    try:
        records = await records_for_autocomplete(thread, interaction.client.user.id)
        if records is None:
            return []
        s = situation_of(registry, records)
    except (MatchError, RecordError, SelectionError, TradeError):
        return []  # not a match thread, or one that cannot be read: nothing to suggest
    except discord.HTTPException as e:
        logger.warning("Reading thread %s for autocomplete failed: %s", thread.id, e)
        return []
    if s.phase.agreed:
        return []
    wanted = current.strip().lower()
    entries = [registry.templates.find(template) for template in remaining(s.phase.pool_ids, s.actions)]
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
