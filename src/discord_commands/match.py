"""The /match commands."""

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.permissions import PRIVATE_THREAD, PUBLIC_THREAD, missing, missing_message
from discord_commands.next_steps import post_next_steps
from discord_commands.thread_log import ThreadLog
from discord_commands.trade import open_only_game
from locks import thread_lock
from rules.formats import Format, Phase
from rules.info import phase_choices
from rules.registry import ModeError, Registry
from rules.selection import SelectionError
from rules.situation import overview, situation_of, unreadable
from rules.start import (
    NOT_IN_A_TEXT_CHANNEL,
    StartError,
    check_opponent,
    choose_phase,
    choose_template,
    coinflip,
    coinflip_announcement,
    match_announcement,
    match_started_text,
    mode_choices,
    private_thread_link,
    rules_announcement,
    template_choices,
    thread_refused_text,
)
from rules.trade import TradeError
from rules.undo import UNDONE_REPLY, UndoError, asked_reply, next_undo, request_text, undone_text, waiting_reply
from state import MatchError, RecordError, describe_records, pending_undo, rebuild

# Players are often slow, so keep the thread open for a week before Discord archives it.
THREAD_ARCHIVE_MINUTES = 10080

MAX_REPLY = 1900  # Discord allows 2000 characters in a message

group = app_commands.Group(name="match", description="Pre-game for a match")


async def begin_match(
    thread: discord.Thread, bot_id: int, registry: Registry, fmt: Format, phase: Phase, template_id: str | None,
    starter, opponent
) -> None:
    """The first messages of a match thread: it started (mentioning both players notifies them), the rules of the
    phase, one message each, and then the coinflip. Only the start and the coinflip are records; the rules are
    plain text for the players."""
    log = ThreadLog(thread, bot_id)
    started = await log.post(
        "match_started",
        match_started_text(starter.mention, opponent.mention, fmt.name, fmt.id, phase.name, template_id),
        p1=starter.id,
        p2=opponent.id,
        mode=fmt.id,
        phase=phase.name,
        template=template_id,
    )
    names = [registry.templates.find(template).name for template in phase.pool_ids]
    template_name = registry.templates.find(template_id).name if template_id else None
    for rule in rules_announcement(phase, template_name, names):
        await thread.send(rule)
    winner, loser = (starter, opponent) if coinflip(starter.id, opponent.id) == starter.id else (opponent, starter)
    flip = await log.post(
        "coinflip",
        coinflip_announcement(winner.mention, loser.mention, phase, template_named=template_id is not None),
        winner=winner.id,
    )
    if template_id is None:
        await post_next_steps(thread, registry, [started, flip])
    else:  # one game and no selection: open its trade, so the players need no command
        await open_only_game(thread, bot_id, registry, [started, flip])


@group.command(name="start", description="Start a match against an opponent")
@app_commands.describe(
    mode="The tournament mode",
    opponent="The player you are playing against",
    phase="The phase of the tournament (only for modes with several phases)",
    template="Play just this template, straight to the trade (one of the phase's templates)",
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
            NOT_IN_A_TEXT_CHANNEL, ephemeral=True
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
            await interaction.followup.send(private_thread_link(opponent.mention, thread.mention))
            await begin_match(thread, bot_id, registry, fmt, chosen_phase, template_id, starter, opponent)
        except discord.Forbidden as e:
            await interaction.followup.send(thread_refused_text(e.text))
    else:
        # A public thread hangs off a message, so first post the message that announces the match.
        await interaction.response.send_message(match_announcement(starter.mention, opponent.mention))
        try:
            announcement = await interaction.original_response()
            thread = await announcement.create_thread(name=title, auto_archive_duration=THREAD_ARCHIVE_MINUTES)
            await begin_match(thread, bot_id, registry, fmt, chosen_phase, template_id, starter, opponent)
        except discord.Forbidden as e:
            # Do not leave an announcement without a thread behind: replace its text with the explanation.
            await interaction.edit_original_response(content=thread_refused_text(e.text))


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
    registry = interaction.client.registry
    try:
        summary = overview(situation_of(registry, records), registry.templates, registry.towns)
    except (MatchError, RecordError, SelectionError, TradeError) as e:
        await interaction.followup.send(unreadable(e))
        return
    listing = describe_records(records)
    # A long match has many records and Discord limits a message, so the list is left out when it does not fit.
    text = f"{summary}\n\n{listing}" if len(summary) + len(listing) < MAX_REPLY else summary
    await interaction.followup.send(text)


@group.command(name="undo", description="Ask to undo the match from a record number; the other player must agree")
@app_commands.rename(from_="from")
@app_commands.describe(from_="Record number to undo from (the 8 in [#8 ...]). Leave out to undo the last step, or to agree")
async def undo(interaction: discord.Interaction, from_: int | None = None) -> None:
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await guarded_records(interaction)  # tells the player to use the match thread
        return

    registry = interaction.client.registry
    async with thread_lock(thread.id):  # one command at a time per thread (see locks.py)
        records = await guarded_records(interaction)
        if records is None:
            return
        try:
            action, plan = next_undo(records, interaction.user.id, from_)
        except UndoError as e:
            await interaction.followup.send(str(e))
            return

        # Only the records are needed to know who the players are, so an undo works even on a thread whose
        # later steps no longer add up (which is when it is most needed).
        match = rebuild(records)
        user = interaction.user
        other_id = match.b if user.id == match.a else match.a
        other = f"<@{other_id}>"
        if action == "waiting":
            await interaction.followup.send(waiting_reply(other))
            return

        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        if action == "request":
            replaces = pending_undo(records) is not None  # a new request overwrites the one that was waiting
            text = request_text(user.mention, other, plan, registry.templates, registry.towns, replaces)
            await log.post("undo_requested", text, player=user.id, start=plan.start)
            await interaction.followup.send(asked_reply(other))
            return

        agreed = await log.post("undone", undone_text(user.mention, plan.start), player=user.id, start=plan.start)
        await interaction.followup.send(UNDONE_REPLY)
        try:
            s = situation_of(registry, records + [agreed])
        except (MatchError, RecordError, SelectionError, TradeError) as e:
            await thread.send(unreadable(e))
            return
        await thread.send(overview(s, registry.templates, registry.towns))
        await post_next_steps(thread, registry, records + [agreed])
