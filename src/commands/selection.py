"""The /ban and /pick commands: template selection inside a match thread."""

from dataclasses import replace

import discord
from discord import app_commands

from commands.common import match_session, start_trade_of
from rules.selection import check_step, is_complete, next_actor, progress, step_text
from state import Event, StateError, fold
from threads import ThreadLog


async def _take_step(interaction: discord.Interaction, action: str, template: str) -> None:
    async with match_session(interaction) as session:
        if session is None:
            return
        match, log = session
        user_id = interaction.user.id
        template_id = check_step(match, user_id, action, template, interaction.client.registry.templates)

        # The text describes the match as it will be after this step.
        after = replace(match, selection=match.selection + [Event(0, action, {"by": user_id, "template": template_id})])
        following = next_actor(after)
        await log.post(
            action,
            step_text(after, user_id, action, template_id),
            ping=f"<@{following}>" if following else None,
            by=user_id,
            template=template_id,
        )
        if is_complete(after):  # the games are known: the trade of the first one starts
            await start_trade_of(after, 1, log, interaction.client)


@app_commands.command(name="ban", description="Ban a template when it is your turn")
@app_commands.describe(template="Template to ban")
async def ban(interaction: discord.Interaction, template: str) -> None:
    await _take_step(interaction, "ban", template)


@app_commands.command(name="pick", description="Pick a template when it is your turn")
@app_commands.describe(template="Template to pick")
async def pick(interaction: discord.Interaction, template: str) -> None:
    await _take_step(interaction, "pick", template)


async def _remaining_templates(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Offer only the templates still in the pool of the match in this thread."""
    client = interaction.client
    if not isinstance(interaction.channel, discord.Thread):
        return []
    try:
        match = fold(await ThreadLog(interaction.channel, client.user.id).read(), client.registry.formats)
    except StateError:
        return []
    wanted = current.lower()
    return [app_commands.Choice(name=t, value=t) for t in progress(match).remaining if wanted in t.lower()][:25]


ban.autocomplete("template")(_remaining_templates)
pick.autocomplete("template")(_remaining_templates)
