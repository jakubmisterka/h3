"""The trade of a game: the town pair and rolling it, the town bid, the color bid, and the gold they move.

Plain Python: no Discord objects in here, so tests can cover it. Nothing about a trade is stored
anywhere but the thread's records: `replay_trades` turns those records into the trades of the match,
checking every one, and everything else (the section, the gold, who plays what) is worked out from them.

A trade runs in sections: first the roll (a player may pay the roll cost to the opponent to get a new pair of
towns, banning towns of the current pair), then the town bid, then the color bid. The roll section ends when
nobody can or wants to roll any more, and reporting the town bid ends it too.

Only one trade is open at a time. Starting a trade closes the open one, which keeps what was recorded and
counts as incomplete; starting it again reopens it where it stopped.
"""

import random
from dataclasses import dataclass, replace
from typing import Callable

from rules.catalogue import Catalogue
from rules.difficulty import ALL_RANDOM_DIFFICULTY, starting_gold
from rules.ledger import GOLD_STEP, Payment, gold_after
from rules.roll_rules import DEFAULT_ROLL_RULES, RollRules
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
class Roll:
    """A roll: who paid the roll cost, the towns they banned, and the new pair the bot drew."""

    player: int
    bans: tuple[str, ...]
    pair: tuple[str, str]


@dataclass(frozen=True)
class Trade:
    game: int  # 1, 2, 3...
    template: str  # template id of the game
    first_pair: tuple[str, str]  # the two town ids the bot drew when the trade started
    players: tuple[int, int]  # (A, B)
    start_gold: int
    rules: RollRules = DEFAULT_ROLL_RULES  # the roll rules of this template in this phase
    rolls: tuple[Roll, ...] = ()
    skipped: tuple[int, ...] = ()  # the players who gave up their remaining rolls
    reports: tuple[Report, ...] = ()

    @property
    def pair(self) -> tuple[str, str]:
        """The pair that stands: the last one drawn."""
        return self.rolls[-1].pair if self.rolls else self.first_pair

    @property
    def banned(self) -> tuple[str, ...]:
        """Every town banned in a roll so far; they stay out of the draw for the rest of the roll section."""
        return tuple(town for roll in self.rolls for town in roll.bans)

    @property
    def gold(self) -> dict[int, int]:
        """The gold of both players: the rolls are paid first, then the bids."""
        payments = [Payment(roll.player, self.rules.roll_cost) for roll in self.rolls]
        payments += [Payment(r.winner, r.amount) for r in self.reports]
        return gold_after(self.start_gold, self.players, payments)

    def rolls_used(self, player: int) -> int:
        return sum(1 for roll in self.rolls if roll.player == player)

    def why_cannot_roll(self, player: int) -> str | None:
        """Why this player may not roll now, or None if they may."""
        if player in self.skipped:
            return "You have skipped your rolls."
        if self.rolls_used(player) >= self.rules.rolls_per_player:
            return f"You have no roll left ({self.rules.rolls_per_player} per player)."
        have = self.gold[player]
        if have < self.rules.roll_cost:
            return f"A roll costs {self.rules.roll_cost} gold and you have {have}."
        return None

    @property
    def rollers(self) -> tuple[int, ...]:
        """The players who may roll now."""
        return tuple(player for player in self.players if self.why_cannot_roll(player) is None)

    @property
    def section(self) -> str | None:
        """The section expected next ("town_roll", "town_bid", "color_bid"), or None when the trade is finished."""
        if not self.reports and self.rollers:
            return "town_roll"
        return REPORTED_SECTIONS[len(self.reports)] if len(self.reports) < len(REPORTED_SECTIONS) else None

    @property
    def finished(self) -> bool:
        return self.section is None

    def other(self, player: int) -> int:
        return self.players[1] if player == self.players[0] else self.players[0]

    def with_report(self, report: Report) -> "Trade":
        """This trade after one more report (not checked here: see `check_report`)."""
        return replace(self, reports=self.reports + (report,))

    def with_roll(self, roll: Roll) -> "Trade":
        """This trade after one more roll (not checked here: see `check_roll`)."""
        return replace(self, rolls=self.rolls + (roll,))

    def with_skip(self, player: int) -> "Trade":
        return replace(self, skipped=self.skipped + (player,))


@dataclass(frozen=True)
class TradeLog:
    """All the trades of a match, by game number, and which one is open (None: nothing has been started)."""

    trades: dict[int, Trade]
    open_game: int | None = None

    @property
    def open(self) -> Trade | None:
        return self.trades[self.open_game] if self.open_game is not None else None


def draw_pair(
    allowed_towns: tuple[str, ...], random_source: random.Random | None = None, banned: tuple[str, ...] = ()
) -> tuple[str, str]:
    """Two different towns at random from the allowed ones that are not banned, each equally likely."""
    available = [town for town in dict.fromkeys(allowed_towns) if town not in banned]
    if len(available) < 2:
        raise TradeError("At least two different towns must be left to draw a pair.")
    first, second = (random_source or random).sample(available, 2)
    return first, second


def _count_towns(number: int) -> str:
    return f"{number} town" if number == 1 else f"{number} towns"


def _town_names(towns: Catalogue, ids) -> str:
    return ", ".join(towns.find(town).name for town in ids)


# --- rolling -------------------------------------------------------------------------------------------------


def _roll_section_over(trade: Trade) -> TradeError:
    if trade.finished:
        return TradeError(f"The trade of game {trade.game} is finished.")
    return TradeError(f"The roll section is over. The {trade.section.replace('_', ' ')} is expected now.")


def check_roll(trade: Trade, roll: Roll, allowed_towns: tuple[str, ...]) -> None:
    """Raise TradeError unless `roll` fits the trade: the roll section is open, the player may roll, the bans are
    towns of the current pair within the limit, and the new pair is two different allowed towns that are not banned."""
    if trade.section != "town_roll":
        raise _roll_section_over(trade)
    if roll.player not in trade.players:
        raise TradeError("Only one of the two players of this game can roll.")
    reason = trade.why_cannot_roll(roll.player)
    if reason:
        raise TradeError(reason)
    if len(set(roll.bans)) != len(roll.bans):
        raise TradeError("A town can only be banned once.")
    if len(roll.bans) > trade.rules.max_roll_bans:
        raise TradeError(f"At most {_count_towns(trade.rules.max_roll_bans)} may be banned in a roll.")
    if not set(roll.bans) <= set(trade.pair):
        raise TradeError("Only towns of the current pair can be banned.")
    banned = trade.banned + roll.bans
    if len(set(roll.pair)) != 2 or not set(roll.pair) <= set(allowed_towns) or set(roll.pair) & set(banned):
        raise TradeError("The new pair must be two different allowed towns that are not banned.")


def make_roll(
    trade: Trade,
    towns: Catalogue,
    allowed_towns: tuple[str, ...],
    player: int,
    ban_texts: list[str],
    random_source: random.Random | None = None,
) -> Roll:
    """A player's roll with the towns they name to ban, checked, with the new pair drawn. Nobody pays on a refusal."""
    if trade.section != "town_roll":
        raise _roll_section_over(trade)
    if player not in trade.players:
        raise TradeError("Only one of the two players of this game can roll.")
    reason = trade.why_cannot_roll(player)
    if reason:
        raise TradeError(reason)
    bans = []
    for text in ban_texts:
        entry = towns.find(text)
        if entry is None:
            raise TradeError(f"{text!r} is not a town. The current pair is {_town_names(towns, trade.pair)}.")
        if entry.id not in trade.pair:
            raise TradeError(
                f"{entry.name} is not in the current pair, so it cannot be banned. The pair is {_town_names(towns, trade.pair)}."
            )
        bans.append(entry.id)
    bans = tuple(dict.fromkeys(bans))  # naming a town twice bans it once
    if len(bans) > trade.rules.max_roll_bans:
        raise TradeError(f"At most {_count_towns(trade.rules.max_roll_bans)} may be banned in a roll.")
    try:
        pair = draw_pair(allowed_towns, random_source, trade.banned + bans)
    except TradeError:
        raise TradeError("Fewer than two allowed towns would be left after those bans, so nobody rolled and nobody paid.") from None
    roll = Roll(player, bans, pair)
    check_roll(trade, roll, allowed_towns)
    return roll


def make_skip(trade: Trade, player: int) -> None:
    """Raise TradeError unless `player` has remaining rolls they can give up."""
    if trade.section != "town_roll":
        raise _roll_section_over(trade)
    if player not in trade.players:
        raise TradeError("Only one of the two players of this game can skip a roll.")
    if player not in trade.rollers:
        raise TradeError(trade.why_cannot_roll(player))


# --- checking a report --------------------------------------------------------------------------------


def expected_report_section(trade: Trade) -> str | None:
    """The bid whose result a report may carry now. While the roll section is open, a town bid report is allowed:
    it counts as skipping every roll still open."""
    return "town_bid" if trade.section == "town_roll" else trade.section


def check_report(trade: Trade, report: Report) -> None:
    """Raise TradeError (or LedgerError) unless `report` fits the trade: the expected section, a player who wins,
    a possible choice and an amount the winner can pay. Rules that depend on the format are checked before this."""
    if trade.finished:
        raise TradeError(f"The trade of game {trade.game} is finished.")
    expected = expected_report_section(trade)
    if report.section != expected:
        raise TradeError(f"The {expected.replace('_', ' ')} is expected now.")
    if report.winner not in trade.players:
        raise TradeError("The winner must be one of the two players of this match.")
    if report.section == "town_bid" and report.choice not in trade.pair:
        raise TradeError("The town chosen must be one of the pair.")
    if report.section == "color_bid" and report.choice not in COLORS:
        raise TradeError("The color must be red or blue.")
    payments = [Payment(roll.player, trade.rules.roll_cost) for roll in trade.rolls]
    payments += [Payment(r.winner, r.amount) for r in trade.reports] + [Payment(report.winner, report.amount)]
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
    expected = expected_report_section(trade)
    is_color = choice_text.strip().lower() in COLORS
    if expected == "town_bid":
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
    report = Report(expected, reporter, winner, amount, choice)
    check_report(trade, report)
    return report


# --- the trades of a match, from its records ------------------------------------------------------------


def _starting_gold(template_id: str, templates: Catalogue) -> int:
    difficulty = templates.find(template_id).details["difficulty"]
    if difficulty == ALL_RANDOM_DIFFICULTY:
        raise TradeError("The trade of a 200% game (only a toss for color) is not available yet.")
    return starting_gold(difficulty)


def new_trade(
    game: int,
    games: tuple[str, ...],
    pair: tuple[str, str],
    players: tuple[int, int],
    templates: Catalogue,
    rules: RollRules = DEFAULT_ROLL_RULES,
) -> Trade:
    """The trade of a game that is starting now."""
    template = games[game - 1]
    return Trade(game, template, pair, players, _starting_gold(template, templates), rules)


def replay_trades(
    records: tuple[Record, ...],
    games: tuple[str, ...],
    players: tuple[int, int],
    templates: Catalogue,
    allowed_towns: tuple[str, ...],
    rules_of: Callable[[str], RollRules],
) -> TradeLog:
    """The trades recorded in a thread, checked one record at a time. `games` are the templates known so far,
    `allowed_towns` the towns of the phase and `rules_of` gives the roll rules of a template.

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
                trades[game] = new_trade(game, games, record.data["pair"], players, templates, rules_of(games[game - 1]))
                open_game = game
            elif game not in trades:
                raise TradeError(f"the trade of game {game} was never started")
            elif record.type == "trade_resumed":
                open_game = game
            else:
                if game != open_game:
                    raise TradeError(f"the trade of game {game} was not open")
                trade = trades[game]
                if record.type == "roll":
                    roll = Roll(record.data["player"], tuple(record.data["bans"]), tuple(record.data["pair"]))
                    check_roll(trade, roll, allowed_towns)
                    trades[game] = trade.with_roll(roll)
                elif record.type == "roll_skipped":
                    make_skip(trade, record.data["player"])
                    trades[game] = trade.with_skip(record.data["player"])
                else:
                    section = record.type
                    choice = record.data["town"] if section == "town_bid" else record.data["color"]
                    report = Report(section, record.data["reporter"], record.data["winner"], record.data["amount"], choice)
                    check_report(trade, report)
                    trades[game] = trade.with_report(report)
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


def _pair_words(towns: Catalogue, pair: tuple[str, str]) -> str:
    first, second = (towns.find(town) for town in pair)
    return f"{first.name} (`{first.id}`) vs {second.name} (`{second.id}`)"


def opening_line(trade: Trade, resumed: bool, mentions: dict[int, str], towns: Catalogue, templates: Catalogue) -> str:
    """The text of the record posted when a trade is opened for the first time or reopened.

    The first two `quoted` words are the town ids of the pair, which is how the pair is read back
    (when reopened, it is the pair that stands now).
    """
    name = templates.find(trade.template).name
    what = "the trade continues" if resumed else "the trade starts"
    gold = _difference_line(trade, mentions) if resumed else _starting_gold_line(trade, mentions)
    pair = trade.pair if resumed else trade.first_pair
    return f"Game {trade.game} ({name}): {what}. Pair: {_pair_words(towns, pair)}. {gold}"


def _who_may_roll(trade: Trade, mentions: dict[int, str]) -> str:
    rollers = trade.rollers
    if len(rollers) == 2:
        return "Both players may roll."
    return f"{mentions[rollers[0]]} may roll."


def prompt(trade: Trade, mentions: dict[int, str], towns: Catalogue) -> str:
    """What to do next in an unfinished trade. The first player (A) bids first in every game; this is a provisional rule."""
    if trade.section == "town_roll":
        rules = trade.rules
        return (
            f"Game {trade.game} town roll. A roll costs {rules.roll_cost} gold. {_who_may_roll(trade, mentions)} "
            f"Roll with /trade roll (banning up to {_count_towns(rules.max_roll_bans)} of the pair), or skip with /trade skip-roll."
        )
    raise_by = f"{mentions[trade.players[0]]} bids first, raising by at least {GOLD_STEP}."
    if trade.section == "town_bid":
        return f"Game {trade.game} town bid: {_town_names(towns, trade.pair)}. {raise_by} Report the result with /trade report."
    return f"Game {trade.game} color bid. {raise_by} Report the result with /trade report, choosing red or blue."


def roll_line(trade: Trade, roll: Roll, mentions: dict[int, str], towns: Catalogue) -> str:
    """The text of the record posted for a roll; `trade` is the trade including the roll.

    The first mention is the roller; the `quoted` words are the banned towns, then the two of the new pair.
    """
    roller, other = mentions[roll.player], mentions[trade.other(roll.player)]
    bans = ", ".join(f"{towns.find(t).name} (`{t}`)" for t in roll.bans)
    banning = f"rolled, banning {bans}," if roll.bans else "rolled without banning a town,"
    return (
        f"Game {trade.game} - {roller} {banning} and paid {trade.rules.roll_cost} gold to {other}. "
        f"New pair: {_pair_words(towns, roll.pair)}.\n{_difference_line(trade, mentions)}"
    )


def skip_line(trade: Trade, player: int, mentions: dict[int, str]) -> str:
    """The text of the record posted when a player gives up their remaining rolls. The first mention is the player."""
    return f"Game {trade.game} - {mentions[player]} skips the roll."


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
    return summary(trade, mentions, towns, templates) if trade.finished else prompt(trade, mentions, towns)
