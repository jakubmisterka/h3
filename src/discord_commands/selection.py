"""The /ban and /pick commands: Template Selection, one step at a time."""

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.next_steps import post_next_steps
from discord_commands.thread_log import ThreadLog, logger, records_for_autocomplete
from locks import thread_lock
from rules.info import AUTOCOMPLETE_LIMIT
from rules.selection import NOT_A_STEP, SelectionError, check_action, choose_available, remaining, step_reply, step_text
from rules.situation import situation_of
from rules.trade import TradeError
from state import MatchError, RecordError


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
            if not s.has_selection:
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
        posted = await log.post(
            do,
            step_text(interaction.user.mention, do, name, template_id),
            player=interaction.user.id,
            template=template_id,
        )
        await post_next_steps(thread, registry, records + [posted])
        await interaction.followup.send(step_reply(do, name))


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
    if not s.has_selection:
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
