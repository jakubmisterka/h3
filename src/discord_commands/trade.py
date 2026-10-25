"""The /trade commands: starting the trade of a game and reporting the result of a bid.

Only one trade is open at a time (see `rules/trade.py`). `/trade start` opens a game's trade, closing the
open one as incomplete; `/trade roll` and `/trade skip-roll` work the roll section, and `/trade report`
reports a bid of the open trade.
"""

import random

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.thread_log import ThreadLog, logger, records_for_autocomplete
from locks import thread_lock
from rules.info import AUTOCOMPLETE_LIMIT
from rules.ledger import LedgerError
from rules.selection import SelectionError
from rules.situation import Situation, situation_of
from rules.trade import (
    COLORS,
    TradeError,
    check_startable,
    choose_game,
    draw_pair,
    expected_report_section,
    make_report,
    make_roll,
    make_skip,
    new_trade,
    next_message,
    opening_line,
    prompt,
    report_line,
    roll_line,
    skip_line,
)
from state import MatchError, RecordError

# Everything that means "tell the player why this cannot be done, and change nothing".
REFUSALS = (MatchError, RecordError, SelectionError, TradeError, LedgerError)

# The random source for the pairs the bot draws. None: the system's. Tests set a seeded one.
random_source: random.Random | None = None

group = app_commands.Group(name="trade", description="The trade of a game: starting it and reporting bids")


async def load(interaction: discord.Interaction, records) -> Situation | None:
    """The situation of the thread, or None after telling the player why not."""
    try:
        return situation_of(interaction.client.registry, records)
    except REFUSALS as e:
        await interaction.followup.send(str(e))
        return None


@group.command(name="start", description="Open the trade of a game (a number or a template; leave out for the next game)")
@app_commands.describe(game="The game number (1, 2, ...) or its template. Leave out for the first game not finished")
async def start(interaction: discord.Interaction, game: str | None = None) -> None:
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await guarded_records(interaction)  # tells the player to use the match thread
        return

    registry = interaction.client.registry
    async with thread_lock(thread.id):  # one command at a time per thread (see locks.py)
        records = await guarded_records(interaction)
        if records is None:
            return
        s = await load(interaction, records)
        if s is None:
            return
        try:
            number = choose_game(game, s.games, s.phase.best_of, s.log, registry.templates)
            kind = check_startable(s.log, number)
            if kind == "start":
                pair = draw_pair(s.phase.allowed_towns, random_source)
                rules = s.roll_rules(s.games[number - 1])
                trade = new_trade(number, s.games, pair, s.players, registry.templates, rules)  # refuses before anything is posted
            else:
                trade = s.log.trades[number]
        except REFUSALS as e:
            await interaction.followup.send(str(e))
            return

        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        text = opening_line(trade, kind == "resume", s.mentions, registry.towns, registry.templates)
        if kind == "start":
            await log.post("trade_started", text, game=number, pair=trade.pair)
        else:
            await log.post("trade_resumed", text, game=number)
        previous = s.log.open
        if previous is not None and not previous.finished:
            await thread.send(f"The trade of game {previous.game} is closed, not finished. Start it again to continue.")
        await thread.send(prompt(trade, s.mentions, registry.towns))
        await interaction.followup.send(f"Game {number}'s trade is open.")


@group.command(name="report", description="Report the result of a bid in the open trade")
@app_commands.describe(
    winner="The player who won the bid",
    amount="What the winner pays the other player, in gold (whole hundreds; 0 if nobody bid)",
    choice="The winner's choice: a town of the pair for the town bid, red or blue for the color bid",
)
async def report(interaction: discord.Interaction, winner: discord.Member, amount: int, choice: str) -> None:
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await guarded_records(interaction)
        return

    registry = interaction.client.registry
    async with thread_lock(thread.id):
        records = await guarded_records(interaction)
        if records is None:
            return
        s = await load(interaction, records)
        if s is None:
            return
        try:
            trade = s.log.open
            if trade is None:
                raise TradeError("No trade is open. Start one with /trade start.")
            made = make_report(
                trade, registry.towns, s.phase.allowed_towns, interaction.user.id, winner.id, amount, choice
            )
        except REFUSALS as e:
            await interaction.followup.send(str(e))
            return

        after = trade.with_report(made)
        rolls_skipped = trade.section == "town_roll"  # reporting the town bid skips every roll still open
        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        data = {"town": made.choice} if made.section == "town_bid" else {"color": made.choice}
        await log.post(
            made.section,
            report_line(after, made, s.mentions, registry.towns),
            game=trade.game,
            reporter=made.reporter,
            winner=made.winner,
            amount=made.amount,
            **data,
        )
        if rolls_skipped:
            await thread.send(f"Game {trade.game}: the rolls still open were skipped.")
        await thread.send(next_message(after, s.mentions, registry.towns, registry.templates))
        await interaction.followup.send("Reported.")


@group.command(name="roll", description="Pay the roll cost to get a new pair of towns, banning towns of the current pair")
@app_commands.describe(
    ban_1="A town of the current pair to ban (leave out to roll without banning)",
    ban_2="A second town of the current pair to ban",
)
async def roll(interaction: discord.Interaction, ban_1: str | None = None, ban_2: str | None = None) -> None:
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await guarded_records(interaction)
        return

    registry = interaction.client.registry
    async with thread_lock(thread.id):
        records = await guarded_records(interaction)
        if records is None:
            return
        s = await load(interaction, records)
        if s is None:
            return
        try:
            trade = s.log.open
            if trade is None:
                raise TradeError("No trade is open. Start one with /trade start.")
            made = make_roll(
                trade, registry.towns, s.phase.allowed_towns, interaction.user.id, [b for b in (ban_1, ban_2) if b], random_source
            )
        except REFUSALS as e:
            await interaction.followup.send(str(e))
            return

        after = trade.with_roll(made)
        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        await log.post(
            "roll",
            roll_line(after, made, s.mentions, registry.towns),
            game=trade.game,
            player=made.player,
            bans=made.bans,
            pair=made.pair,
        )
        await thread.send(next_message(after, s.mentions, registry.towns, registry.templates))
        await interaction.followup.send("Rolled.")


@group.command(name="skip-roll", description="Give up your remaining rolls in this trade (the trade itself goes on)")
async def skip_roll(interaction: discord.Interaction) -> None:
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        await guarded_records(interaction)
        return

    registry = interaction.client.registry
    async with thread_lock(thread.id):
        records = await guarded_records(interaction)
        if records is None:
            return
        s = await load(interaction, records)
        if s is None:
            return
        try:
            trade = s.log.open
            if trade is None:
                raise TradeError("No trade is open. Start one with /trade start.")
            make_skip(trade, interaction.user.id)
        except REFUSALS as e:
            await interaction.followup.send(str(e))
            return

        after = trade.with_skip(interaction.user.id)
        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        await log.post("roll_skipped", skip_line(after, interaction.user.id, s.mentions), game=trade.game, player=interaction.user.id)
        await thread.send(next_message(after, s.mentions, registry.towns, registry.templates))
        await interaction.followup.send("You skip the roll.")


# --- what is offered while typing ---------------------------------------------------------------------------


async def _situation_for_options(interaction: discord.Interaction) -> Situation | None:
    """The situation, for suggestions. Any problem just means no suggestions."""
    thread = interaction.channel
    if not isinstance(thread, discord.Thread):
        return None
    try:
        records = await records_for_autocomplete(thread, interaction.client.user.id)
        return situation_of(interaction.client.registry, records) if records is not None else None
    except REFUSALS:
        return None  # not a match thread, or one that cannot be read: nothing to suggest
    except discord.HTTPException as e:
        logger.warning("Reading thread %s for autocomplete failed: %s", thread.id, e)
        return None


@start.autocomplete("game")
async def _game_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    s = await _situation_for_options(interaction)
    if s is None:
        return []
    templates = interaction.client.registry.templates
    choices = []
    for number, template_id in enumerate(s.games, start=1):
        trade = s.log.trades.get(number)
        if trade is not None and trade.finished:
            continue
        label = f"Game {number}: {templates.find(template_id).name}"
        if current.strip().lower() in label.lower():
            choices.append(app_commands.Choice(name=label, value=str(number)))
    return choices[:AUTOCOMPLETE_LIMIT]


async def _ban_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """The towns of the current pair, for the two ban options."""
    s = await _situation_for_options(interaction)
    trade = s.log.open if s else None
    if trade is None or trade.section != "town_roll":
        return []
    towns = interaction.client.registry.towns
    wanted = current.strip().lower()
    return [
        app_commands.Choice(name=towns.find(town).name, value=town)
        for town in trade.pair
        if wanted in towns.find(town).name.lower()
    ]


roll.autocomplete("ban_1")(_ban_options)
roll.autocomplete("ban_2")(_ban_options)


@report.autocomplete("choice")
async def _choice_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    s = await _situation_for_options(interaction)
    trade = s.log.open if s else None
    if trade is None or trade.finished:
        return []
    towns = interaction.client.registry.towns
    if expected_report_section(trade) == "town_bid":  # also during the roll section: reporting the town bid skips the rolls
        options = [(towns.find(town).name, town) for town in trade.pair]
    else:
        options = [(color, color) for color in COLORS]
    wanted = current.strip().lower()
    return [app_commands.Choice(name=name, value=value) for name, value in options if wanted in name.lower()]
