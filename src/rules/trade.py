"""The trade of a game: the town pair, the town bid, the color bid, and the gold they move.

Plain Python: no Discord objects in here, so tests can cover it. Nothing about a trade is stored
anywhere but the thread's records: `replay_trades` turns those records into the trades of the match,
checking every one, and everything else (the section, the gold, who plays what) is worked out from them.

Only one trade is open at a time. Starting a trade closes the open one, which keeps what was recorded and
counts as incomplete; starting it again reopens it where it stopped. Rolling the town pair comes later,
so for now the pair the bot drew is the pair that is bid on.
"""

import random
from dataclasses import dataclass, replace

from rules.catalogue import Catalogue
from rules.difficulty import ALL_RANDOM_DIFFICULTY, starting_gold
from rules.ledger import GOLD_STEP, Payment, gold_after
from state import Record

COLORS = ("red", "blue")  # red moves first
REPORTED_SECTIONS = ("town_bid", "color_bid")  # the sections whose result the players report, in order


class TradeError(ValueError):
    """The trade cannot do what was asked. The message is shown to the player."""


@dataclass(frozen=True)
class Report:
    """The result of a bid: who won it, for how much, and what they chose (a town id, or "red"/"blue")."""

    section: str  # "town_bid" or "color_bid"
    reporter: int
    winner: int
    amount: int
    choice: str


@dataclass(frozen=True)
class Trade:
    game: int  # 1, 2, 3...
    template: str  # template id of the game
    pair: tuple[str, str]  # the two town ids the bot drew
    players: tuple[int, int]  # (A, B)
    start_gold: int
    reports: tuple[Report, ...] = ()

    @property
    def gold(self) -> dict[int, int]:
        return gold_after(self.start_gold, self.players, [Payment(r.winner, r.amount) for r in self.reports])

    @property
    def section(self) -> str | None:
        """The section whose result is expected next, or None when the trade is finished."""
        return REPORTED_SECTIONS[len(self.reports)] if len(self.reports) < len(REPORTED_SECTIONS) else None

    @property
    def finished(self) -> bool:
        return self.section is None

    def other(self, player: int) -> int:
        return self.players[1] if player == self.players[0] else self.players[0]

    def with_report(self, report: Report) -> "Trade":
        """This trade after one more report (not checked here: see `check_report`)."""
        return replace(self, reports=self.reports + (report,))


@dataclass(frozen=True)
class TradeLog:
    """All the trades of a match, by game number, and which one is open (None: nothing has been started)."""

    trades: dict[int, Trade]
    open_game: int | None = None

    @property
    def open(self) -> Trade | None:
        return self.trades[self.open_game] if self.open_game is not None else None


def draw_pair(allowed_towns: tuple[str, ...], random_source: random.Random | None = None) -> tuple[str, str]:
    """Two different towns at random, each allowed town equally likely."""
    if len(set(allowed_towns)) < 2:
        raise TradeError("At least two different towns must be allowed to draw a pair.")
    first, second = (random_source or random).sample(list(allowed_towns), 2)
    return first, second


# --- checking a report --------------------------------------------------------------------------------


def _town_names(towns: Catalogue, ids) -> str:
    return ", ".join(towns.find(town).name for town in ids)


def check_report(trade: Trade, report: Report) -> None:
    """Raise TradeError (or LedgerError) unless `report` fits the trade: the expected section, a player who wins,
    a possible choice and an amount the winner can pay. Rules that depend on the format are checked before this."""
    if trade.finished:
        raise TradeError(f"The trade of game {trade.game} is finished.")
    if report.section != trade.section:
        raise TradeError(f"The {trade.section.replace('_', ' ')} is expected now.")
    if report.winner not in trade.players:
        raise TradeError("The winner must be one of the two players of this match.")
    if report.section == "town_bid" and report.choice not in trade.pair:
        raise TradeError("The town chosen must be one of the pair.")
    if report.section == "color_bid" and report.choice not in COLORS:
        raise TradeError("The color must be red or blue.")
    payments = [Payment(r.winner, r.amount) for r in trade.reports] + [Payment(report.winner, report.amount)]
    gold_after(trade.start_gold, trade.players, payments)  # refuses an amount the winner cannot pay


def make_report(
    trade: Trade,
    towns: Catalogue,
    allowed_towns: tuple[str, ...],
    reporter: int,
    winner: int,
    amount: int,
    choice_text: str,
) -> Report:
    """A player's report, checked, with a message that says what to do when it does not fit."""
    if trade.finished:
        raise TradeError(f"The trade of game {trade.game} is finished.")
    is_color = choice_text.strip().lower() in COLORS
    if trade.section == "town_bid":
        if is_color:
            raise TradeError(f"The town bid comes first. Choose a town of the pair: {_town_names(towns, trade.pair)}.")
        entry = towns.find(choice_text)
        if entry is None or entry.id not in allowed_towns:
            raise TradeError(f"{choice_text!r} is not an allowed town. Allowed towns: {_town_names(towns, allowed_towns)}.")
        if entry.id not in trade.pair:
            raise TradeError(f"{entry.name} is not in the pair. The pair is {_town_names(towns, trade.pair)}.")
        choice = entry.id
    else:
        if not is_color:
            raise TradeError("The town bid is done. Now the color bid: choose red or blue.")
        choice = choice_text.strip().lower()
    report = Report(trade.section, reporter, winner, amount, choice)
    check_report(trade, report)
    return report


# --- the trades of a match, from its records ------------------------------------------------------------


def _starting_gold(template_id: str, templates: Catalogue) -> int:
    difficulty = templates.find(template_id).details["difficulty"]
    if difficulty == ALL_RANDOM_DIFFICULTY:
        raise TradeError("The trade of a 200% game (only a toss for color) is not available yet.")
    return starting_gold(difficulty)


def new_trade(game: int, games: tuple[str, ...], pair: tuple[str, str], players: tuple[int, int], templates: Catalogue) -> Trade:
    """The trade of a game that is starting now."""
    template = games[game - 1]
    return Trade(game, template, pair, players, _starting_gold(template, templates))


def replay_trades(
    records: tuple[Record, ...], games: tuple[str, ...], players: tuple[int, int], templates: Catalogue
) -> TradeLog:
    """The trades recorded in a thread, checked one record at a time. `games` are the templates known so far.

    A record that does not fit (a game that is not known, a report for a trade that is not open, a payment that
    could not have been made) means the thread cannot be trusted, and is reported.
    """
    trades: dict[int, Trade] = {}
    open_game = None
    for record in records:
        game = record.game
        try:
            if not 1 <= game <= len(games):
                raise TradeError(f"game {game} is not decided in this match")
            if record.type == "trade_started":
                if game in trades:
                    raise TradeError(f"the trade of game {game} was started twice")
                trades[game] = new_trade(game, games, record.data["pair"], players, templates)
                open_game = game
            elif game not in trades:
                raise TradeError(f"the trade of game {game} was never started")
            elif record.type == "trade_resumed":
                open_game = game
            else:
                if game != open_game:
                    raise TradeError(f"the trade of game {game} was not open")
                section = record.type
                choice = record.data["town"] if section == "town_bid" else record.data["color"]
                report = Report(section, record.data["reporter"], record.data["winner"], record.data["amount"], choice)
                check_report(trades[game], report)
                trades[game] = trades[game].with_report(report)
        except ValueError as e:  # TradeError, or the ledger refusing a payment
            raise TradeError(f"Message #{record.n} (game {game}) does not fit the trade: {e}") from e
    return TradeLog(trades, open_game)


# --- which game a player means ---------------------------------------------------------------------------------


def choose_game(text: str | None, games: tuple[str, ...], best_of: int, log: TradeLog, templates: Catalogue) -> int:
    """The game number a player means by `text`: a number ("2", "game 2") or a template. Raises TradeError.

    Without text it is the first known game whose trade is not finished.
    """
    if not text or not text.strip():
        if not games:
            raise TradeError("No game is decided yet. A game can be traded once its template is picked.")
        for number in range(1, len(games) + 1):
            if number not in log.trades or not log.trades[number].finished:
                return number
        raise TradeError("The trades of all the games decided so far are finished.")

    wanted = text.strip().lower().removeprefix("game").strip()
    if wanted.isdigit():
        number = int(wanted)
        if not 1 <= number <= best_of:
            raise TradeError(f"This match has games 1 to {best_of}, not {number}.")
        if number > len(games):
            raise TradeError(f"The template of game {number} is not decided yet.")
        return number
    entry = templates.find(text)
    if entry is None or entry.id not in games:
        raise TradeError(f"{text!r} is not a game of this match. Name a game number or one of its templates.")
    return games.index(entry.id) + 1


def check_startable(log: TradeLog, game: int) -> str:
    """"start" if the game's trade was never started, "resume" if it was closed. Raises if it cannot be opened."""
    trade = log.trades.get(game)
    if trade is None:
        return "start"
    if trade.finished:
        raise TradeError(f"The trade of game {game} is finished.")
    if log.open_game == game:
        raise TradeError(f"The trade of game {game} is already open.")
    return "resume"


# --- what the thread says --------------------------------------------------------------------------------------
#
# Players think in differences ("I am 900 up"), so after the start the thread shows the gold as the difference
# from the starting gold. The starting gold itself is stated when the trade starts, and is what the checks use.


def signed(amount: int) -> str:
    return f"{amount:+d}" if amount else "0"


def _starting_gold_line(trade: Trade, mentions: dict[int, str]) -> str:
    a, b = trade.players
    return f"Starting gold: {mentions[a]} {trade.start_gold}, {mentions[b]} {trade.start_gold}"


def _difference_line(trade: Trade, mentions: dict[int, str]) -> str:
    gold = trade.gold
    a, b = trade.players
    return f"Gold difference: {mentions[a]} {signed(gold[a] - trade.start_gold)}, {mentions[b]} {signed(gold[b] - trade.start_gold)}"


def opening_line(trade: Trade, resumed: bool, mentions: dict[int, str], towns: Catalogue, templates: Catalogue) -> str:
    """The text of the record posted when a trade is opened for the first time or reopened.

    The first two `quoted` words are the town ids of the pair, which is how the pair is read back.
    """
    name = templates.find(trade.template).name
    first, second = (towns.find(town) for town in trade.pair)
    what = "the trade continues" if resumed else "the trade starts"
    gold = _difference_line(trade, mentions) if resumed else _starting_gold_line(trade, mentions)
    return f"Game {trade.game} ({name}): {what}. Pair: {first.name} (`{first.id}`) vs {second.name} (`{second.id}`). {gold}"


def prompt(trade: Trade, mentions: dict[int, str]) -> str:
    """What to do next in an unfinished trade. The first player (A) bids first in every game; this is a provisional rule."""
    raise_by = f"{mentions[trade.players[0]]} bids first, raising by at least {GOLD_STEP}."
    if trade.section == "town_bid":
        return f"Game {trade.game} town bid. {raise_by} Report the result with /trade report, choosing a town of the pair."
    return f"Game {trade.game} color bid. {raise_by} Report the result with /trade report, choosing red or blue."


def report_line(trade: Trade, report: Report, mentions: dict[int, str], towns: Catalogue) -> str:
    """The text of the record posted for a report; `trade` is the trade including the report.

    The first two mentions are the reporter and the winner, the first two `quoted` words the amount and the choice.
    """
    reporter, winner, loser = mentions[report.reporter], mentions[report.winner], mentions[trade.other(report.winner)]
    if report.section == "town_bid":
        town = towns.find(report.choice)
        other = towns.find(next(t for t in trade.pair if t != report.choice)).name
        decided = f"Town bid, reported by {reporter}: {winner} won at `{report.amount}` gold and plays {town.name} (`{town.id}`), {loser} plays {other}."
    else:
        other = "blue" if report.choice == "red" else "red"
        decided = f"Color bid, reported by {reporter}: {winner} won at `{report.amount}` gold and plays `{report.choice}`, {loser} plays {other}."
    return f"Game {trade.game} - {decided}\n{_difference_line(trade, mentions)}"


def summary(trade: Trade, mentions: dict[int, str], towns: Catalogue, templates: Catalogue) -> str:
    """The lobby settings of a finished trade: each player's town, color and gold difference."""
    town_report, color_report = trade.reports
    plays_town = {town_report.winner: town_report.choice, trade.other(town_report.winner): next(t for t in trade.pair if t != town_report.choice)}
    plays_color = {color_report.winner: color_report.choice, trade.other(color_report.winner): "blue" if color_report.choice == "red" else "red"}
    gold = trade.gold
    lines = [f"Game {trade.game} lobby settings - {templates.find(trade.template).name}"]
    for player in trade.players:
        lines.append(f"{mentions[player]}: {towns.find(plays_town[player]).name}, {plays_color[player]}, gold {signed(gold[player] - trade.start_gold)}")
    return "\n".join(lines)


def next_message(trade: Trade, mentions: dict[int, str], towns: Catalogue, templates: Catalogue) -> str:
    """What the thread says after the trade moved on: what to do next, or the lobby settings when it is done."""
    return summary(trade, mentions, towns, templates) if trade.finished else prompt(trade, mentions)
