"""The trade of a game: the town pair and rolling it, the town bid, the color bid, and the gold they move.

Plain Python: no Discord objects in here, so tests can cover it. Nothing about a trade is stored
anywhere but the thread's records: `replay_trades` turns those records into the trades of the match,
checking every one, and everything else (the section, the gold, who plays what) is worked out from them.

A trade runs in sections, which its kind fixes (`trade_kinds.sections`). The standard trade: first the roll (a
player may pay the roll cost to the opponent to get a new pair of towns, banning towns of the current pair), then
the town bid, then the color bid. A mirror trade draws one town and has only the color bid; a trade with
computer-player packs draws two packs of towns too and has a pack bid between the town and the color bid. The roll
section ends when nobody can or wants to roll any more, and reporting the first bid ends it too.

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
from rules.trade_draw import PACK_SIZE, Draw, TradeError, check_draw, check_start, draw_pair, draw_start
from rules.trade_kinds import PACKS_KIND, SECTION_TABLE, TradeKind, bid_sections
from state import Record

COLORS = ("red", "blue")  # red moves first
PACKS = ("pack1", "pack2")  # the two packs of computer-player towns, which a bid chooses between


###### Wording: short replies and notes ########################################################################
# The sentences the bot says. To change a wording, change it here; the logic that decides when is further down.

REPORTED_REPLY = "Reported."
ROLLED_REPLY = "Rolled."
SKIPPED_REPLY = "You skip the roll."


def opened_reply(game: int) -> str:
    """The private reply to the player who opened the trade of a game."""
    return f"Game {game}'s trade is open."


def closed_note(game: int) -> str:
    """Said in the thread when opening another trade closes a trade that was not finished."""
    return f"The trade of game {game} is closed, not finished. Start it again to continue."


################################################################################################################


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
    """A roll: who paid the roll cost, the towns they banned, and what the bot drew instead."""

    player: int
    bans: tuple[str, ...]
    draw: Draw

    @property
    def towns(self) -> tuple[str, ...]:
        return self.draw.towns

    @property
    def packs(self) -> tuple[str, ...]:
        return self.draw.packs


@dataclass(frozen=True)
class Trade:
    game: int  # 1, 2, 3...
    template: str  # template id of the game
    first_draw: Draw  # what the bot drew when the trade started
    players: tuple[int, int]  # (A, B)
    start_gold: int
    rules: RollRules = DEFAULT_ROLL_RULES  # the roll rules of this template in this phase
    rolls: tuple[Roll, ...] = ()
    skipped: tuple[int, ...] = ()  # the players who passed on the towns that stand now (a roll clears it)
    reports: tuple[Report, ...] = ()
    kind: TradeKind = TradeKind()  # how this trade is run
    mirror: bool = False  # both players play the same town

    @property
    def draw(self) -> Draw:
        """What stands: the last draw (the first one, when nobody has rolled)."""
        return self.rolls[-1].draw if self.rolls else self.first_draw

    @property
    def towns(self) -> tuple[str, ...]:
        """The town(s) the players play, as drawn: two, or one for a mirror."""
        return self.draw.towns

    @property
    def packs(self) -> tuple[str, ...]:
        """The towns of the two packs that stand: the first three are pack1, the last three pack2."""
        return self.draw.packs

    def pack(self, name: str) -> tuple[str, ...]:
        """The three towns of "pack1" or "pack2"."""
        return self.draw.pack(PACKS.index(name))

    @property
    def bids(self) -> tuple[str, ...]:
        """The bids of this kind of trade, in order: the sections whose result the players report."""
        return bid_sections(self.kind, self.mirror)

    @property
    def banned(self) -> tuple[str, ...]:
        """Every town banned in a roll so far. They stay out of the town(s) the players play for the rest of the roll
    section; they may still come up in a pack of computer-player towns."""
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
            return "You have already passed on these towns. You can roll again if your opponent rolls."
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
        """The section expected next ("town_roll", or one of the bids), or None when the trade is finished."""
        if not self.reports and self.rollers:
            return "town_roll"
        return self.bids[len(self.reports)] if len(self.reports) < len(self.bids) else None

    @property
    def finished(self) -> bool:
        return self.section is None

    def other(self, player: int) -> int:
        return self.players[1] if player == self.players[0] else self.players[0]

    def with_report(self, report: Report) -> "Trade":
        """This trade after one more report (not checked here: see `check_report`)."""
        return replace(self, reports=self.reports + (report,))

    def with_roll(self, roll: Roll) -> "Trade":
        """This trade after one more roll (not checked here: see `check_roll`). The towns changed, so every skip made
        for the old ones is over: whoever skipped may roll again."""
        return replace(self, rolls=self.rolls + (roll,), skipped=())

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


def _count_towns(number: int) -> str:
    return f"{number} town" if number == 1 else f"{number} towns"


def pair_names(towns: Catalogue, played: tuple[str, ...]) -> str:
    """The town(s) the players play for a message: "Necropolis vs Tower", or "Necropolis" for a mirror."""
    return " vs ".join(towns.find(town).name for town in played)


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
    if trade.mirror:
        if roll.bans != trade.towns:
            raise TradeError("A roll in a mirror trade bans the town that stands.")
    else:
        if len(roll.bans) > trade.rules.max_roll_bans:
            raise TradeError(f"At most {_count_towns(trade.rules.max_roll_bans)} may be banned in a roll.")
        if not set(roll.bans) <= set(trade.towns):
            raise TradeError("Only towns of the current pair can be banned.")
    check_draw(roll.draw, trade.kind, trade.mirror, allowed_towns, trade.banned + roll.bans)


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
    if trade.mirror:
        if ban_texts:
            raise TradeError(
                f"A roll in a mirror trade names no town: it bans the town that stands ({_town_names(towns, trade.towns)}). "
                "Roll without naming one."
            )
        bans = trade.towns
    else:
        bans = []
        for text in ban_texts:
            entry = towns.find(text)
            if entry is None:
                raise TradeError(f"{text!r} is not a town. The current pair is {_town_names(towns, trade.towns)}.")
            if entry.id not in trade.towns:
                raise TradeError(
                    f"{entry.name} is not in the current pair, so it cannot be banned. The pair is {_town_names(towns, trade.towns)}."
                )
            bans.append(entry.id)
        bans = tuple(dict.fromkeys(bans))  # naming a town twice bans it once
        if len(bans) > trade.rules.max_roll_bans:
            raise TradeError(f"At most {_count_towns(trade.rules.max_roll_bans)} may be banned in a roll.")
    try:
        draw = draw_start(trade.kind, trade.mirror, allowed_towns, random_source, trade.banned + bans)
    except TradeError:
        left = "No allowed town" if trade.mirror else "Fewer than two allowed towns"
        raise TradeError(f"{left} would be left to play after those bans, so nobody rolled and nobody paid.") from None
    roll = Roll(player, bans, draw)
    check_roll(trade, roll, allowed_towns)
    return roll


def make_skip(trade: Trade, player: int) -> None:
    """Raise TradeError unless `player` may roll now, and so may pass on the towns that stand."""
    if trade.section != "town_roll":
        raise _roll_section_over(trade)
    if player not in trade.players:
        raise TradeError("Only one of the two players of this game can skip a roll.")
    if player not in trade.rollers:
        raise TradeError(trade.why_cannot_roll(player))


# --- checking a report --------------------------------------------------------------------------------


def expected_report_section(trade: Trade) -> str | None:
    """The bid whose result a report may carry now. While the roll section is open, a report of the first bid is
    allowed: it counts as skipping every roll still open."""
    return trade.bids[0] if trade.section == "town_roll" else trade.section


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
    if report.section == "town_bid" and report.choice not in trade.towns:
        raise TradeError("The town chosen must be one of the pair.")
    if report.section == "pack_bid" and report.choice not in PACKS:
        raise TradeError("The pack chosen must be pack1 or pack2.")
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
    typed = choice_text.strip().lower()
    is_color = typed in COLORS
    if expected == "town_bid":
        if is_color:
            raise TradeError(f"The town bid comes first. Choose a town of the pair: {_town_names(towns, trade.towns)}.")
        entry = towns.find(choice_text)
        if entry is None or entry.id not in allowed_towns:
            raise TradeError(f"{choice_text!r} is not an allowed town. Allowed towns: {_town_names(towns, allowed_towns)}.")
        if entry.id not in trade.towns:
            raise TradeError(f"{entry.name} is not in the pair. The pair is {_town_names(towns, trade.towns)}.")
        choice = entry.id
    elif expected == "pack_bid":
        if typed not in PACKS:
            raise TradeError("The pack bid is next. Choose pack1 or pack2.")
        choice = typed
    else:
        if not is_color:
            if trade.mirror:
                raise TradeError("Both players play the same town, so only the color is bid. Choose red or blue.")
            if "pack_bid" in trade.bids:
                raise TradeError("The color bid is next. Choose red or blue.")
            raise TradeError("The town bid is done. Now the color bid: choose red or blue.")
        choice = typed
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
    draw: Draw,
    players: tuple[int, int],
    templates: Catalogue,
    rules: RollRules = DEFAULT_ROLL_RULES,
    kind: TradeKind = TradeKind(),
    mirror: bool = False,
) -> Trade:
    """The trade of a game that is starting now, with what the bot drew for it."""
    template = games[game - 1]
    return Trade(game, template, draw, players, _starting_gold(template, templates), rules, kind=kind, mirror=mirror)


def replay_trades(
    records: tuple[Record, ...],
    games: tuple[str, ...],
    players: tuple[int, int],
    templates: Catalogue,
    allowed_towns: tuple[str, ...],
    rules_of: Callable[[str], RollRules],
    kind_of: Callable[[str], TradeKind] = lambda template: TradeKind(),
    towns: Catalogue | None = None,
) -> TradeLog:
    """The trades recorded in a thread, checked one record at a time. `games` are the templates known so far,
    `allowed_towns` the towns of the phase, `rules_of` gives the roll rules of a template and `kind_of` how it is traded.

    The thread quotes towns by name (or, in older threads, by id); with the town catalogue (`towns`) they are read as
    ids. A word that is no town stays as it is, and fails the checks.

    A record that does not fit (a game that is not known, a report for a trade that is not open, a payment that
    could not have been made) means the thread cannot be trusted, and is reported.
    """
    def ids(words) -> tuple[str, ...]:
        return tuple(towns.find(w).id if towns is not None and towns.find(w) else w for w in words)

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
                template = games[game - 1]
                kind, mirror = kind_of(template), bool(templates.find(template).details.get("mirror"))
                draw = Draw(ids(record.data["towns"]), ids(record.data.get("packs", ())))
                check_start(draw, kind, mirror, allowed_towns)
                trades[game] = new_trade(game, games, draw, players, templates, rules_of(template), kind, mirror)
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
                    draw = Draw(ids(record.data["towns"]), ids(record.data.get("packs", ())))
                    roll = Roll(record.data["player"], ids(record.data["bans"]), draw)
                    check_roll(trade, roll, allowed_towns)
                    trades[game] = trade.with_roll(roll)
                elif record.type == "roll_skipped":
                    make_skip(trade, record.data["player"])
                    trades[game] = trade.with_skip(record.data["player"])
                else:
                    section = record.type
                    choice = record.data[SECTION_TABLE[section].choice_field]
                    if section == "town_bid":
                        choice = ids([choice])[0]
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


def _pair_words(towns: Catalogue, played: tuple[str, ...]) -> str:
    """The town(s) the players play, by name in `quotes`, which is how they are read back: "`Castle` vs `Tower`"."""
    return " vs ".join(f"`{towns.find(town).name}`" for town in played)


def _pack_lines(towns: Catalogue, packs: tuple[str, ...]) -> list[str]:
    """The two packs, one line each, for prompts: "Pack1: Castle, Tower, Cove"."""
    draw = Draw((), packs)
    return [
        f"{name.capitalize()}: {', '.join(towns.find(t).name for t in draw.pack(number))}" for number, name in enumerate(PACKS)
    ]


def _draw_lines(trade: Trade, towns: Catalogue, draw: Draw) -> list[str]:
    """What was drawn, one line each, for the record of a trade starting (and of a roll that draws packs). The marker
    words ("Pair:", "Town:", "Pack1:") are how `state.py` finds the towns again; the layout is only for the eyes:

        Pair: `Castle` vs `Tower`
        Pack1: `Rampart`, `Inferno`, `Dungeon`
        Pack2: ...
    """
    lines = [f"{'Town' if trade.mirror else 'Pair'}: {_pair_words(towns, draw.towns)}"]
    if draw.packs:
        for number, name in enumerate(PACKS):
            members = ", ".join(f"`{towns.find(t).name}`" for t in draw.pack(number))
            lines.append(f"{name.capitalize()}: {members}")
    return lines


def _named(towns: Catalogue, ids: tuple[str, ...]) -> tuple[str, ...]:
    """Town ids as the thread quotes them: by name."""
    return tuple(towns.find(town).name for town in ids)


def start_data(trade: Trade, towns: Catalogue) -> dict:
    """The data of the record posted when a trade starts: the words `opening_line` quotes."""
    draw = trade.first_draw
    return {"towns": _named(towns, draw.towns), **({"packs": _named(towns, draw.packs)} if draw.packs else {})}


def roll_data(roll: Roll, towns: Catalogue) -> dict:
    """The data of the record posted for a roll: the words `roll_line` quotes."""
    packs = {"packs": _named(towns, roll.packs)} if roll.packs else {}
    return {"player": roll.player, "bans": _named(towns, roll.bans), "towns": _named(towns, roll.towns), **packs}


def report_data(report: Report, towns: Catalogue) -> dict:
    """The data of the record posted for a report: the words `report_line` quotes."""
    choice = towns.find(report.choice).name if report.section == "town_bid" else report.choice
    return {
        "reporter": report.reporter,
        "winner": report.winner,
        "amount": report.amount,
        SECTION_TABLE[report.section].choice_field: choice,
    }


def opening_line(trade: Trade, resumed: bool, mentions: dict[int, str], towns: Catalogue, templates: Catalogue) -> str:
    """The text of the record posted when a trade is opened for the first time or reopened.

    The first two `quoted` words are the town ids of the pair, which is how the pair is read back
    (when reopened, it is the pair that stands now).
    """
    name = templates.find(trade.template).name
    what = "the trade continues" if resumed else "the trade starts"
    gold = _difference_line(trade, mentions) if resumed else _starting_gold_line(trade, mentions)
    draw = trade.draw if resumed else trade.first_draw
    kind = " (mirror: both players play the same town)" if trade.mirror else ""
    kind += " (with computer-player packs)" if trade.kind.name == PACKS_KIND else ""
    return "\n".join([f"Game {trade.game} ({name}): {what}{kind}.", *_draw_lines(trade, towns, draw), gold])


def _who_may_roll(trade: Trade, mentions: dict[int, str]) -> str:
    rollers = trade.rollers
    if len(rollers) == 2:
        return "Both players may roll."
    return f"{mentions[rollers[0]]} may roll."


def prompt(trade: Trade, mentions: dict[int, str], towns: Catalogue, show_draw: bool = True) -> str:
    """What to do next in an unfinished trade, a few short lines. The first player (A) bids first in every game; this
    is a provisional rule.

    The roll section says what was drawn only when `show_draw` is true. The message that drew it (the start of the
    trade, a roll) is right above the prompt, so repeating it would only say it twice; after an undo it is not.
    """
    game = f"Game {trade.game}"
    if trade.section == "town_roll":
        rules = trade.rules
        if not show_draw:
            head = []  # what was drawn is said right above, and the roll is the only question
        elif trade.packs:
            head = [f"{game} town roll", f"Pair: {pair_names(towns, trade.towns)}", *_pack_lines(towns, trade.packs)]
        elif trade.mirror:
            head = [f"{game} town roll: {pair_names(towns, trade.towns)}, played by both"]
        else:
            head = [f"{game} town roll: {pair_names(towns, trade.towns)}"]
        bans = "it bans this town" if trade.mirror else f"banning up to {_count_towns(rules.max_roll_bans)} of the pair"
        return "\n".join(
            [
                *head,
                f"A roll costs {rules.roll_cost} gold. {_who_may_roll(trade, mentions)}",
                f"Roll with /trade roll ({bans}), or skip with /trade skip-roll.",
            ]
        )
    raise_by = f"{mentions[trade.players[0]]} bids first, raising by at least {GOLD_STEP}."
    if trade.section == "town_bid":
        lines = [f"{game} town bid: {pair_names(towns, trade.towns)}", raise_by, "Report the result with /trade report."]
    elif trade.section == "pack_bid":
        lines = [
            f"{game} pack bid",
            *_pack_lines(towns, trade.packs),
            raise_by,
            "Report the result with /trade report, choosing pack1 or pack2.",
        ]
    else:
        lines = [f"{game} color bid", raise_by, "Report the result with /trade report, choosing red or blue."]
    return "\n".join(lines)


def roll_line(trade: Trade, roll: Roll, mentions: dict[int, str], towns: Catalogue) -> str:
    """The text of the record posted for a roll; `trade` is the trade including the roll.

    The first mention is the roller; the `quoted` words before "New pair:" (or "New town:") are the banned towns, the
    ones after it the new town(s), and then the packs.
    """
    roller, other = mentions[roll.player], mentions[trade.other(roll.player)]
    bans = ", ".join(f"`{towns.find(t).name}`" for t in roll.bans)
    banning = f"rolled, banning {bans}," if roll.bans else "rolled without banning a town,"
    paid = f"Game {trade.game} - {roller} {banning} and paid {trade.rules.roll_cost} gold to {other}."
    drawn = _draw_lines(trade, towns, roll.draw)
    drawn[0] = ("New town:" if trade.mirror else "New pair:") + drawn[0].split(":", 1)[1]
    return "\n".join([paid, *drawn, _difference_line(trade, mentions)])


def skip_line(trade: Trade, player: int, mentions: dict[int, str], by_report: bool = False) -> str:
    """The text of the record posted when a player passes on the towns that stand. The first mention is the player.
    `by_report` says the skip is because the town bid was reported while the roll was still open."""
    reason = " (the town bid was reported)" if by_report else ""
    return f"Game {trade.game} - {mentions[player]} skips the roll{reason}."


def report_line(trade: Trade, report: Report, mentions: dict[int, str], towns: Catalogue) -> str:
    """The text of the record posted for a report; `trade` is the trade including the report.

    The first two mentions are the reporter and the winner, the first two `quoted` words the amount and the choice.
    """
    reporter, winner, loser = mentions[report.reporter], mentions[report.winner], mentions[trade.other(report.winner)]
    won = f"{winner} won at `{report.amount}` gold and"
    if report.section == "town_bid":
        town = towns.find(report.choice)
        other = towns.find(next(t for t in trade.towns if t != report.choice)).name
        what, lines = "Town bid", [f"{won} plays `{town.name}`", f"{loser} plays {other}"]
    elif report.section == "pack_bid":
        other = PACKS[1 - PACKS.index(report.choice)]
        what, lines = "Pack bid", [f"{won} takes `{report.choice}`", f"{loser} gets {other}"]
    else:
        other = "blue" if report.choice == "red" else "red"
        what, lines = "Color bid", [f"{won} plays `{report.choice}`", f"{loser} plays {other}"]
    return "\n".join([f"Game {trade.game} - {what}, reported by {reporter}", *lines, _difference_line(trade, mentions)])


def summary(
    trade: Trade, mentions: dict[int, str], towns: Catalogue, templates: Catalogue, lobby: list[str] | tuple = ()
) -> str:
    """The lobby settings of a finished trade: the settings typed into the lobby (`lobby`, one line each, when they are
    stated), then each player's town, color and gold difference."""
    reports = {report.section: report for report in trade.reports}
    color_report = reports["color_bid"]
    plays_color = {color_report.winner: color_report.choice, trade.other(color_report.winner): "blue" if color_report.choice == "red" else "red"}
    plays_town, plays_pack = {}, {}
    if "town_bid" in reports:
        town_report = reports["town_bid"]
        plays_town = {town_report.winner: town_report.choice, trade.other(town_report.winner): next(t for t in trade.towns if t != town_report.choice)}
    if "pack_bid" in reports:
        pack_report = reports["pack_bid"]
        plays_pack = {pack_report.winner: pack_report.choice, trade.other(pack_report.winner): PACKS[1 - PACKS.index(pack_report.choice)]}
    gold = trade.gold
    lines = [f"Game {trade.game} lobby settings - {templates.find(trade.template).name}", *lobby]
    if trade.mirror:
        lines.append(f"Town (both players): {towns.find(trade.towns[0]).name}")
    for player in trade.players:
        parts = []
        if player in plays_town:
            parts.append(towns.find(plays_town[player]).name)
        if player in plays_pack:
            pack = plays_pack[player]
            parts.append(f"{pack} ({', '.join(towns.find(t).name for t in trade.pack(pack))})")
        parts += [plays_color[player], f"gold {signed(gold[player] - trade.start_gold)}"]
        lines.append(f"{mentions[player]}: {', '.join(parts)}")
    return "\n".join(lines)


def next_words(trade: Trade, towns: Catalogue) -> str:
    """What comes next in an unfinished trade, for the match status: ", next: town bid Castle vs Tower (rolls still open)".
    The roll is a side option until the first bid is reported, so the first bid is what comes next."""
    if trade.finished:
        return ""
    bid = trade.bids[len(trade.reports)]
    rolls = " (rolls still open)" if trade.section == "town_roll" else ""
    if bid == "town_bid":
        return f", next: town bid {pair_names(towns, trade.towns)}{rolls}"
    return f", next: {bid.replace('_', ' ')}{rolls}"


def next_message(
    trade: Trade,
    mentions: dict[int, str],
    towns: Catalogue,
    templates: Catalogue,
    lobby: list[str] | tuple = (),
    show_draw: bool = True,
) -> str:
    """What the thread says after the trade moved on: what to do next, or the lobby settings when it is done."""
    if trade.finished:
        return summary(trade, mentions, towns, templates, lobby)
    return prompt(trade, mentions, towns, show_draw)
