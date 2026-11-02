"""The /trade commands: starting the trade of a game and reporting the result of a bid.

Only one trade is open at a time (see `rules/trade.py`). `/trade start` opens a game's trade, closing the
open one as incomplete; `/trade roll` and `/trade skip-roll` work the roll section, and `/trade report`
reports a bid of the open trade.
"""

import random

import discord
from discord import app_commands

from discord_commands.guard import guarded_records
from discord_commands.next_steps import post_next_steps
from discord_commands.thread_log import ThreadLog, logger, records_for_autocomplete
from locks import thread_lock
from rules.info import AUTOCOMPLETE_LIMIT
from rules.ledger import LedgerError
from rules.selection import SelectionError
from rules.situation import Situation, situation_of
from rules.template_facts import announcement_lines, setting_line
from rules.trade_draw import draw_start
from rules.trade import (
    BANNED_REPLY,
    COLORS,
    NOBODY_BANNED_REPLY,
    PACKS,
    REPORTED_REPLY,
    ROLLED_REPLY,
    SKIPPED_REPLY,
    Trade,
    TradeError,
    check_startable,
    choose_game,
    closed_note,
    expected_report_section,
    hero_bans_data,
    hero_bans_line,
    hero_pool,
    heroes_drawn_data,
    heroes_drawn_line,
    make_hero_ban,
    make_heroes_drawn,
    make_report,
    make_roll,
    make_skip,
    new_trade,
    opened_reply,
    opening_line,
    report_line,
    roll_line,
    report_data,
    roll_data,
    skip_line,
    start_data,
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


def prepare_opening(registry, s: Situation, number: int) -> tuple[str, Trade]:
    """What opening the trade of a game needs: "start" or "resume", and the trade. Raises when it cannot be opened.
    Nothing is posted yet, so a refusal leaves the thread as it was."""
    kind = check_startable(s.log, number)
    if kind == "resume":
        return kind, s.log.trades[number]
    template = s.games[number - 1]
    settings = s.settings(template)
    trade_kind, mirror = settings.trade, settings.mirror
    draw = draw_start(
        trade_kind, mirror, s.phase.allowed_towns, random_source, heroes=registry.heroes, template=registry.templates.find(template)
    )
    return kind, new_trade(number, s.games, draw, s.players, registry.templates, s.roll_rules(template), trade_kind, mirror)


async def post_opening(
    thread, bot_id: int, registry, s: Situation, records, number: int, opening: tuple[str, Trade], facts: bool = False
) -> None:
    """Open the trade of a game in the thread: its record, a note if another trade is closed, and what comes next.
    With `facts` the lines about the template (timer, download, how the trade is run) come before the record: the message
    that announced the game left them out, and a match started with a template has said them already."""
    kind, trade = opening
    log = ThreadLog(thread, bot_id)
    log.last_n = records[-1].n
    text = opening_line(trade, kind == "resume", s.mentions, registry.towns, registry.templates, registry.heroes)
    if kind == "start" and facts and (lines := announcement_lines(s.settings(trade.template), None, registry.templates)):
        await thread.send("\n".join(lines))
    if kind == "start":
        posted = await log.post("trade_started", text, game=number, **start_data(trade, registry.towns, registry.heroes))
    else:
        posted = await log.post("trade_resumed", text, game=number)
    previous = s.log.open
    if previous is not None and not previous.finished:
        await thread.send(closed_note(previous.game))
    if kind == "start" and (rules := setting_line("additional_rules", s.settings(trade.template))):
        await thread.send(rules)  # once, when the trade of the game first starts (not when it is resumed)
    await finish_step(thread, bot_id, registry, records + [posted])


async def finish_step(thread, bot_id: int, registry, records) -> None:
    """End a command that moved a trade on: if the heroes of a roulette are due (the rolls and the bans are over), the
    bot draws and posts them, and then the thread says what comes next."""
    try:
        s = situation_of(registry, records)
        trade = s.log.open
        if trade is not None and trade.section == "hero_draw":
            drawn = make_heroes_drawn(trade, registry.heroes, registry.templates, random_source)
            log = ThreadLog(thread, bot_id)
            log.last_n = records[-1].n
            text = heroes_drawn_line(trade, drawn, registry.towns, registry.heroes)
            posted = await log.post("heroes_drawn", text, game=trade.game, **heroes_drawn_data(drawn, registry.heroes))
            records = records + [posted]
    except TradeError as e:
        await thread.send(str(e))  # for example too few heroes: the format check should have refused it
    except REFUSALS:
        pass  # the thread cannot be read: post_next_steps says so
    await post_next_steps(thread, registry, records)


async def open_only_game(thread, bot_id: int, registry, records) -> None:
    """For a match that started with a named template: open the trade of its one game, so nobody needs a command.
    Where that is not possible (a 200% game has no trade yet) the thread says so."""
    try:
        s = situation_of(registry, records)
        opening = prepare_opening(registry, s, 1)
    except REFUSALS as e:
        await thread.send(str(e))
        return
    await post_opening(thread, bot_id, registry, s, records, 1, opening)


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
            number = choose_game(game, s.games, s.total_games, s.log, registry.templates)
            opening = prepare_opening(registry, s, number)
        except REFUSALS as e:
            await interaction.followup.send(str(e))
            return

        await post_opening(thread, interaction.client.user.id, registry, s, records, number, opening, facts=True)
        await interaction.followup.send(opened_reply(number))


@group.command(name="report", description="Report the result of a bid in the open trade")
@app_commands.describe(
    winner="The player who won the bid",
    amount="What the winner pays the other player, in gold (whole hundreds; 0 if nobody bid)",
    choice="The winner's choice: a town of the pair, pack1 or pack2 for the pack bid, red or blue for the color bid",
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

        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        # Reporting the town bid skips every roll still open. Each skip is recorded, so undoing the bid alone
        # does not open the roll section again.
        skips = []
        for player in trade.rollers if trade.section == "town_roll" else ():
            trade = trade.with_skip(player)
            skips.append(
                await log.post("roll_skipped", skip_line(trade, player, s.mentions, by_report=True), game=trade.game, player=player)
            )
        after = trade.with_report(made)
        posted = await log.post(
            made.section,
            report_line(after, made, s.mentions, registry.towns),
            game=trade.game,
            **report_data(made, registry.towns),
        )
        await finish_step(thread, interaction.client.user.id, registry, records + skips + [posted])
        await interaction.followup.send(REPORTED_REPLY)


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
                trade, registry.towns, s.phase.allowed_towns, interaction.user.id, [b for b in (ban_1, ban_2) if b], random_source,
                registry.heroes, registry.templates,
            )
        except REFUSALS as e:
            await interaction.followup.send(str(e))
            return

        after = trade.with_roll(made)
        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        posted = await log.post(
            "roll", roll_line(after, made, s.mentions, registry.towns, registry.heroes),
            game=trade.game,
            **roll_data(made, registry.towns, registry.heroes),
        )
        await finish_step(thread, interaction.client.user.id, registry, records + [posted])
        await interaction.followup.send(ROLLED_REPLY)


@group.command(name="skip-roll", description="Pass on the towns that stand (you can roll again if your opponent rolls)")
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
        posted = await log.post(
            "roll_skipped", skip_line(after, interaction.user.id, s.mentions), game=trade.game, player=interaction.user.id
        )
        await finish_step(thread, interaction.client.user.id, registry, records + [posted])
        await interaction.followup.send(SKIPPED_REPLY)


@group.command(name="ban-heroes", description="Ban heroes of the drawn towns before the heroes are drawn (none: ban nobody)")
@app_commands.describe(
    hero_1="A hero to ban (leave out to ban nobody)",
    hero_2="A second hero to ban",
    hero_3="A third hero to ban",
)
async def ban_heroes(
    interaction: discord.Interaction, hero_1: str | None = None, hero_2: str | None = None, hero_3: str | None = None
) -> None:
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
            names = [name for name in (hero_1, hero_2, hero_3) if name]
            made = make_hero_ban(trade, registry.heroes, registry.templates, interaction.user.id, names)
        except REFUSALS as e:
            await interaction.followup.send(str(e))
            return

        log = ThreadLog(thread, interaction.client.user.id)
        log.last_n = records[-1].n
        text = hero_bans_line(trade, made, s.mentions, registry.heroes)
        posted = await log.post("hero_bans", text, game=trade.game, **hero_bans_data(made, registry.heroes))
        await finish_step(thread, interaction.client.user.id, registry, records + [posted])
        await interaction.followup.send(BANNED_REPLY if made.heroes else NOBODY_BANNED_REPLY)


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
    if trade is None or trade.section != "town_roll" or trade.mirror:  # a mirror's roll names no town
        return []
    towns = interaction.client.registry.towns
    wanted = current.strip().lower()
    return [
        app_commands.Choice(name=towns.find(town).name, value=town)
        for town in trade.towns
        if wanted in towns.find(town).name.lower()
    ]


async def _hero_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """The heroes that can be banned now: those of the drawn town(s) that the template's map offers."""
    s = await _situation_for_options(interaction)
    trade = s.log.open if s else None
    if trade is None or trade.section != "hero_bans":
        return []
    registry = interaction.client.registry
    wanted = current.strip().lower()
    choices = []
    for town, ids in hero_pool(trade, registry.heroes, registry.templates).items():
        for hero_id in ids:
            hero = registry.heroes.find(hero_id)
            label = f"{hero.name} ({registry.towns.find(town).name})"
            if wanted in label.lower():
                choices.append(app_commands.Choice(name=label, value=hero.name))
    return choices[:AUTOCOMPLETE_LIMIT]


for _option in ("hero_1", "hero_2", "hero_3"):
    ban_heroes.autocomplete(_option)(_hero_options)

roll.autocomplete("ban_1")(_ban_options)
roll.autocomplete("ban_2")(_ban_options)


@report.autocomplete("choice")
async def _choice_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    s = await _situation_for_options(interaction)
    trade = s.log.open if s else None
    if trade is None or trade.finished:
        return []
    towns = interaction.client.registry.towns
    if trade.section in ("hero_bans", "hero_draw"):  # the bid waits for the heroes
        return []
    expected = expected_report_section(trade)  # also during the roll section: reporting the first bid skips the rolls
    if expected == "town_bid":
        options = [(towns.find(town).name, town) for town in trade.towns]
    elif expected == "pack_bid":
        options = [(f"{name}: {', '.join(towns.find(t).name for t in trade.pack(name))}", name) for name in PACKS]
    elif expected == "first_choice_bid":
        options = [("hero", "hero"), ("color", "color")]
    else:
        options = [(color, color) for color in COLORS]
    wanted = current.strip().lower()
    return [app_commands.Choice(name=name, value=value) for name, value in options if wanted in name.lower()]
