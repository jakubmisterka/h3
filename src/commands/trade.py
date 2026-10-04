"""The /trade commands: roll, bids, colors and undo, inside a match thread."""

import re

import discord
from discord import app_commands

from commands.common import match_session, post_action, start_trade_of
from rules import trade
from state import Match, StateError, fold
from threads import ThreadLog

group = app_commands.Group(name="trade", description="The trade before a game: roll, bids and colors")

def game_option():
    """A fresh decorator each time: discord.py keeps the descriptions in a dict that must not be shared."""
    return app_commands.describe(game="Game number (default: the first game whose trade is not finished)")


async def _run(interaction: discord.Interaction, game: int | None, build) -> None:
    """Run one trade request: check it, post the event, then start the next game's trade if this one ended."""
    async with match_session(interaction) as session:
        if session is None:
            return
        match, log = session
        number = trade.choose_game(match, game)
        action = build(match, number, interaction.client.registry.factions)
        await post_action(log, action)
        match = trade.after(match, number, action.type, action.data)
        await _continue_after(match, number, log, interaction.client)


async def _continue_after(match: Match, number: int, log: ThreadLog, client) -> None:
    if trade.trade_state(match, number).complete:
        following = trade.following_game(match, number)
        if following:
            await start_trade_of(match, following, log, client)


@group.command(name="start", description="Start the trade of a game (the bot draws the faction pair)")
@game_option()
async def start(interaction: discord.Interaction, game: int | None = None) -> None:
    async with match_session(interaction) as session:
        if session is None:
            return
        match, log = session
        number = game or trade.first_unstarted(match)
        if number is None:
            raise trade.TradeError("The trade of every game has already started.")
        await start_trade_of(match, number, log, interaction.client)


@group.command(name="roll", description="Pay for a roll: ban up to 2 factions of the pair and get a new pair")
@app_commands.describe(bans="Factions to ban, separated by commas (optional)")
@game_option()
async def roll(interaction: discord.Interaction, bans: str | None = None, game: int | None = None) -> None:
    ban_texts = [b for b in re.split(r"[,;]+", bans or "") if b.strip()]
    user = interaction.user.id
    await _run(interaction, game, lambda m, n, f: trade.roll(m, n, user, ban_texts, f))


@group.command(name="decline", description="Say you do not want to roll")
@game_option()
async def decline(interaction: discord.Interaction, game: int | None = None) -> None:
    user = interaction.user.id
    await _run(interaction, game, lambda m, n, f: trade.decline(m, n, user, f))


@group.command(name="report", description="Report the result of a bid (or the color you chose after the toss)")
@app_commands.describe(
    choice="The faction chosen, or the color (red or blue)",
    winner="Who won the bid",
    amount="Gold the winner pays to the opponent",
)
@game_option()
async def report(
    interaction: discord.Interaction,
    choice: str,
    winner: discord.Member | None = None,
    amount: int | None = None,
    game: int | None = None,
) -> None:
    user = interaction.user.id
    winner_id = winner.id if winner else None
    await _run(interaction, game, lambda m, n, f: trade.report(m, n, user, choice, winner_id, amount, f))


@group.command(name="undo", description="Undo the latest report (rolls and random results cannot be undone)")
@app_commands.describe(game="Game number (default: the game with the latest activity)")
async def undo(interaction: discord.Interaction, game: int | None = None) -> None:
    user = interaction.user.id
    async with match_session(interaction) as session:
        if session is None:
            return
        match, log = session
        number = game or trade.latest_game(match)
        if number is None:
            raise trade.TradeError("No trade has started yet, so there is nothing to undo.")
        action = trade.undo(match, number, user, interaction.client.registry.factions)
        await post_action(log, action)


@group.command(name="status", description="Show where the trade of a game stands")
@game_option()
async def status(interaction: discord.Interaction, game: int | None = None) -> None:
    async with match_session(interaction) as session:
        if session is None:
            return
        match, log = session
        number = trade.choose_game(match, game)
        await log.say(trade.status_text(match, number, interaction.client.registry.factions))


@report.autocomplete("choice")
async def _choice_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Offer the pair's factions while bidding for a faction, and red/blue for colors."""
    client = interaction.client
    if not isinstance(interaction.channel, discord.Thread):
        return []
    try:
        match = fold(await ThreadLog(interaction.channel, client.user.id).read(), client.registry.formats)
        number = trade.first_unfinished(match)
        state = trade.trade_state(match, number) if number else None
    except (StateError, ValueError):
        return []
    if state is None or not state.started:
        return []
    if state.section in ("faction_roll", "faction_bid") and state.pair:
        options = [(client.registry.factions.name_of(f), f) for f in state.pair]
    else:
        options = [(c, c) for c in trade.COLORS]
    return [app_commands.Choice(name=n, value=v) for n, v in options if current.lower() in n.lower()]
