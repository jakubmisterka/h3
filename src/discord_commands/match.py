"""The /match commands."""

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.permissions import PRIVATE_THREAD, PUBLIC_THREAD, missing, missing_message
from discord_commands.thread_log import ThreadLog
from rules.formats import Format, Phase
from rules.info import phase_choices
from rules.registry import ModeError, Registry
from rules.start import (
    StartError,
    check_opponent,
    choose_phase,
    choose_template,
    coinflip,
    coinflip_announcement,
    mode_choices,
    rules_announcement,
    template_choices,
)
from state import describe_match, describe_records, rebuild

# Players are often slow, so keep the thread open for a week before Discord archives it.
THREAD_ARCHIVE_MINUTES = 10080

group = app_commands.Group(name="match", description="Pre-game for a match")


def refused_message(error: discord.Forbidden) -> str:
    """Text for a refusal we did not predict. The permission check below catches the usual causes first."""
    return f"Discord refused to create the thread ({error.text}). Please ask a server admin to check my permissions."


async def begin_match(
    thread: discord.Thread, bot_id: int, registry: Registry, fmt: Format, phase: Phase, template_id: str | None,
    starter, opponent
) -> None:
    """The first messages of a match thread: it started (mentioning both players notifies them), the coinflip,
    and the rules of the phase. Only the first two are records; the rules are plain text for the players."""
    log = ThreadLog(thread, bot_id)
    wording = f"Mode: {fmt.name} (`{fmt.id}`), phase `{phase.name}`"
    if template_id:
        wording += f", template `{template_id}`"
    await log.post(
        "match_started",
        f"Match started: {starter.mention} vs {opponent.mention}. {wording}. This is your match thread.",
        p1=starter.id,
        p2=opponent.id,
        mode=fmt.id,
        phase=phase.name,
        template=template_id,
    )
    winner, loser = (starter, opponent) if coinflip(starter.id, opponent.id) == starter.id else (opponent, starter)
    await log.post(
        "coinflip",
        coinflip_announcement(winner.mention, loser.mention, phase),
        winner=winner.id,
    )
    names = [registry.templates.find(template).name for template in phase.pool_ids]
    template_name = registry.templates.find(template_id).name if template_id else None
    await thread.send(rules_announcement(phase, template_name, names))


@group.command(name="start", description="Start a match against an opponent")
@app_commands.describe(
    mode="The tournament mode",
    opponent="The player you are playing against",
    phase="The phase of the tournament (only for modes with several phases)",
    template="The template you agreed on (only for modes where players agree on it)",
)
async def start(
    interaction: discord.Interaction,
    mode: str,
    opponent: discord.Member,
    phase: str | None = None,
    template: str | None = None,
) -> None:
    starter = interaction.user
    channel = interaction.channel
    title = f"{starter.display_name} vs {opponent.display_name}"[:100]
    registry = interaction.client.registry

    try:
        check_opponent(starter.id, opponent.id, opponent.bot)
        fmt = registry.choose_mode(mode)
        chosen_phase = choose_phase(fmt, phase)
        template_id = choose_template(chosen_phase, template, registry.templates)
    except (StartError, ModeError) as e:
        await interaction.response.send_message(str(e), ephemeral=True)
        return
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "Start a match in a normal text channel, not inside a thread.", ephemeral=True
        )
        return

    # Check the bot's permissions here first, so nothing is posted before we find out it cannot finish.
    private = fmt.thread_visibility == "private"
    lacking = missing(interaction.app_permissions, PRIVATE_THREAD if private else PUBLIC_THREAD)
    if lacking:
        await interaction.response.send_message(missing_message(lacking), ephemeral=True)
        return

    bot_id = interaction.client.user.id
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
            await begin_match(thread, bot_id, registry, fmt, chosen_phase, template_id, starter, opponent)
        except discord.Forbidden as e:
            await interaction.followup.send(refused_message(e))
    else:
        # A public thread hangs off a message, so first post the message that announces the match.
        await interaction.response.send_message(f"Match: {starter.mention} vs {opponent.mention}")
        try:
            announcement = await interaction.original_response()
            thread = await announcement.create_thread(name=title, auto_archive_duration=THREAD_ARCHIVE_MINUTES)
            await begin_match(thread, bot_id, registry, fmt, chosen_phase, template_id, starter, opponent)
        except discord.Forbidden as e:
            # Do not leave an announcement without a thread behind: replace its text with the explanation.
            await interaction.edit_original_response(content=refused_message(e))


@start.autocomplete("mode")
async def _mode_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    choices = mode_choices(interaction.client.registry, current)
    return [app_commands.Choice(name=name, value=value) for name, value in choices]


@start.autocomplete("phase")
async def _phase_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    choices = phase_choices(interaction.client.registry, interaction.namespace.mode or "", current)
    return [app_commands.Choice(name=name, value=value) for name, value in choices]


@start.autocomplete("template")
async def _template_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    mode, phase = interaction.namespace.mode or "", interaction.namespace.phase
    choices = template_choices(interaction.client.registry, mode, phase, current)
    return [app_commands.Choice(name=name, value=value) for name, value in choices]


@group.command(name="status", description="Show what the bot has recorded in this match thread")
async def status(interaction: discord.Interaction) -> None:
    records = await guarded_records(interaction)  # replies to the user itself when it says no
    if records is None:
        return
    summary = describe_match(rebuild(records))  # the guard has already checked that this works
    await interaction.followup.send(f"{summary}\n\n{describe_records(records)}")
