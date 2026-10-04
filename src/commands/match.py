"""The /match commands: start a match, with its thread and coinflip."""

import discord
from discord import app_commands

from commands.common import start_trade_of
from rules.errors import UserError
from rules.formats import get_mode, list_modes
from rules.selection import is_complete, next_actor, start_text
from rules.start import coinflip, plan_start
from state import fold, make_event
from threads import ThreadLog

THREAD_ARCHIVE_MINUTES = 10080  # 7 days; players are often slow


group = app_commands.Group(name="match", description="Pre-game for a match")


@group.command(name="start", description="Start the pre-game: coinflip, bans, picks and trade")
@app_commands.describe(
    mode="Tournament or ranked mode",
    opponent="The player you are playing against",
    phase="Phase of the tournament (only for modes with several phases)",
    template="Agreed template (only for modes where players agree on it)",
)
async def start(
    interaction: discord.Interaction,
    mode: str,
    opponent: discord.Member,
    phase: str | None = None,
    template: str | None = None,
) -> None:
    client = interaction.client
    channel = interaction.channel
    starter = interaction.user

    try:
        found = client.registry.find_format(mode)
        fmt = get_mode(client.registry.formats, found.id if found else mode)
        plan = plan_start(fmt, phase, template, client.registry.templates, starter.id, opponent.id, opponent.bot)
    except UserError as e:
        await interaction.response.send_message(str(e), ephemeral=True)
        return
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "Start matches in a normal text channel, not inside a thread.", ephemeral=True
        )
        return

    await interaction.response.defer()
    title = f"{fmt.name}: {starter.display_name} vs {opponent.display_name}"[:100]
    try:
        if fmt.thread_visibility == "private":
            thread = await channel.create_thread(
                name=title,
                type=discord.ChannelType.private_thread,
                invitable=False,
                auto_archive_duration=THREAD_ARCHIVE_MINUTES,
            )
            await thread.add_user(starter)
            await thread.add_user(opponent)
            await interaction.followup.send(f"Match thread for {starter.mention} vs {opponent.mention}: {thread.mention}")
        else:
            message = await interaction.followup.send(
                f"Match started: {starter.mention} vs {opponent.mention}", wait=True
            )
            thread = await message.create_thread(name=title, auto_archive_duration=THREAD_ARCHIVE_MINUTES)
    except discord.Forbidden:
        await interaction.followup.send(
            "I am not allowed to create threads here. A server admin needs to give me the "
            "permissions to create and send messages in threads.",
            ephemeral=True,
        )
        return

    async with client.locks.hold(thread.id):
        log = ThreadLog(thread, client.user.id)
        data = {"format": fmt.id, "phase": plan.phase.name, "p1": starter.id, "p2": opponent.id}
        if plan.template:
            data["template"] = plan.template
        started = await log.post(
            "match_started",
            f"**{fmt.name}**, {plan.phase.name} (best of {plan.phase.best_of}): {starter.mention} vs {opponent.mention}",
            ping=f"{starter.mention} {opponent.mention}",
            **data,
        )

        # Work out what the match looks like after the coinflip, to say what comes next.
        a, b = coinflip(starter.id, opponent.id)
        flipped = make_event(log.last_n + 1, "coinflip", a=a, b=b)
        match = fold([started, flipped], client.registry.formats)
        text = f"<@{a}> won the coinflip and is player **A**. <@{b}> is player **B**.\n{start_text(match)}"
        await log.post("coinflip", text, ping=f"<@{next_actor(match)}>" if next_actor(match) else None, a=a, b=b)
        if is_complete(match):  # agreed template: no bans or picks, the trade of game 1 starts
            await start_trade_of(match, 1, log, client)


@start.autocomplete("mode")
async def _mode_choices(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    modes = list_modes(interaction.client.registry.formats)
    return [app_commands.Choice(name=m.name, value=m.id) for m in modes if current.lower() in m.name.lower()][:25]


@start.autocomplete("phase")
async def _phase_choices(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    fmt = interaction.client.registry.find_format(interaction.namespace.mode or "")
    if fmt is None:
        return []
    return [app_commands.Choice(name=p.name, value=p.name) for p in fmt.phases if current.lower() in p.name.lower()]


@start.autocomplete("template")
async def _template_choices(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    registry = interaction.client.registry
    fmt = registry.find_format(interaction.namespace.mode or "")
    if fmt is None:
        return []
    pool = sorted({t for p in fmt.phases if p.agreed for t in p.pool})
    return [
        app_commands.Choice(name=registry.templates.name_of(t), value=t) for t in pool if current.lower() in t.lower()
    ][:25]
