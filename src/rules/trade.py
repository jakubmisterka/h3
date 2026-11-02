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

from rules.catalogue import Catalogue, heroes_offered
from rules.difficulty import ALL_RANDOM_DIFFICULTY, starting_gold
from rules.ledger import GOLD_STEP, Payment, gold_after, spaced
from rules.roll_rules import DEFAULT_ROLL_RULES, RollRules
from rules.trade_draw import (
    PACK_SIZE,
    Draw,
    HeroDrawError,
    TradeError,
    check_draw,
    check_heroes_fit,
    check_start,
    draw_pair,
    draw_start,
    hero_pool_of,
    pick_heroes,
)
from rules.trade_kinds import SECTION_TABLE, TradeKind, bid_sections
from state import Record

COLORS = ("red", "blue")  # red moves first
PACKS = ("pack1", "pack2")  # the two packs of computer-player towns, which a bid chooses between
FIRST_CHOICES = ("hero", "color")  # what the winner of a mirror roulette's bid chooses first


###### Wording: short replies and notes ########################################################################
# The sentences the bot says. To change a wording, change it here; the logic that decides when is further down.

REPORTED_REPLY = "Reported."
ROLLED_REPLY = "Rolled."
SKIPPED_REPLY = "You skip the roll."
BANNED_REPLY = "Banned."
NOBODY_BANNED_REPLY = "You ban nobody."


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
class HeroBan:
    """The heroes a player banned before the draw (hero ids). Banning nobody is a ban of no heroes."""

    player: int
    heroes: tuple[str, ...]


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
    hero_bans: tuple[HeroBan, ...] = ()  # roulette: the players' bans, the first player (A) first
    drawn_heroes: tuple[str, ...] = ()  # roulette: the heroes the bot drew after the rolls and the bans (hero ids)

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
    def heroes_after_rolls(self) -> bool:
        """A roulette whose heroes are banned and drawn once the roll section is over."""
        return self.kind.draws_heroes and self.kind.roll_before_heroes

    @property
    def banned_heroes(self) -> tuple[str, ...]:
        """Every hero the players banned so far."""
        return tuple(hero for ban in self.hero_bans for hero in ban.heroes)

    @property
    def heroes(self) -> tuple[str, ...]:
        """The heroes of the game as they stand: drawn with the towns, or after the rolls and the bans (hero ids)."""
        with_the_towns = self.kind.draws_heroes and not self.kind.roll_before_heroes
        return self.draw.heroes if with_the_towns else self.drawn_heroes

    @property
    def ban_turn(self) -> int | None:
        """The player who must ban heroes now (A, then B), or None when it is nobody's turn."""
        if self.section != "hero_bans":
            return None
        return self.players[len(self.hero_bans)]

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
            return "You have already skipped. You can roll again if your opponent rolls."
        if self.rolls_used(player) >= self.rules.rolls_per_player:
            return f"You have no roll left ({self.rules.rolls_per_player} per player)."
        have = self.gold[player]
        if have < self.rules.roll_cost:
            return f"A roll costs {spaced(self.rules.roll_cost)} gold and you have {spaced(have)}."
        return None

    @property
    def rollers(self) -> tuple[int, ...]:
        """The players who may roll now."""
        return tuple(player for player in self.players if self.why_cannot_roll(player) is None)

    @property
    def section(self) -> str | None:
        """The section expected next ("town_roll", "hero_bans", "hero_draw" (the bot is to draw the heroes), or one of
        the bids), or None when the trade is finished."""
        if not self.reports and self.rollers:
            return "town_roll"
        if self.heroes_after_rolls and not self.reports:
            if self.kind.hero_bans and len(self.hero_bans) < len(self.players):
                return "hero_bans"
            if not self.drawn_heroes:
                return "hero_draw"
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

    def with_hero_ban(self, ban: HeroBan) -> "Trade":
        """This trade after one more hero ban (not checked here: see `check_hero_ban`)."""
        return replace(self, hero_bans=self.hero_bans + (ban,))

    def with_heroes(self, heroes: tuple[str, ...]) -> "Trade":
        """This trade after the heroes were drawn (not checked here: see `check_heroes_drawn`)."""
        return replace(self, drawn_heroes=heroes)

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


def check_roll(
    trade: Trade, roll: Roll, allowed_towns: tuple[str, ...], heroes: Catalogue | None = None, templates: Catalogue | None = None
) -> None:
    """Raise TradeError unless `roll` fits the trade: the roll section is open, the player may roll, the bans are
    towns of the current pair within the limit, and the new pair is two different allowed towns that are not banned.
    With the hero catalogue and the templates, the heroes a roll draws with the towns are checked as well."""
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
    template = templates.find(trade.template) if templates is not None else None
    check_draw(roll.draw, trade.kind, trade.mirror, allowed_towns, trade.banned + roll.bans, heroes, template)


def make_roll(
    trade: Trade,
    towns: Catalogue,
    allowed_towns: tuple[str, ...],
    player: int,
    ban_texts: list[str],
    random_source: random.Random | None = None,
    heroes: Catalogue | None = None,
    templates: Catalogue | None = None,
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
        template = templates.find(trade.template) if templates is not None else None
        draw = draw_start(trade.kind, trade.mirror, allowed_towns, random_source, trade.banned + bans, heroes, template)
    except HeroDrawError as e:
        raise TradeError(f"{e} Nobody rolled and nobody paid.") from None
    except TradeError:
        left = "No allowed town" if trade.mirror else "Fewer than two allowed towns"
        raise TradeError(f"{left} would be left to play after those bans, so nobody rolled and nobody paid.") from None
    roll = Roll(player, bans, draw)
    check_roll(trade, roll, allowed_towns, heroes, templates)
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


def _heroes_first(trade: Trade) -> None:
    """In a roulette the bid comes after the heroes are banned and drawn, so a report before that is refused."""
    if trade.heroes_after_rolls and trade.section in ("town_roll", "hero_bans", "hero_draw"):
        raise TradeError(
            "In a roulette the heroes are banned and drawn before the bid. "
            + {
                "town_roll": "Finish the roll section first: roll, or skip the roll.",
                "hero_bans": "The heroes are banned now: ban them with /trade ban-heroes.",
                "hero_draw": "The heroes are being drawn.",
            }[trade.section]
        )


def check_report(trade: Trade, report: Report) -> None:
    """Raise TradeError (or LedgerError) unless `report` fits the trade: the expected section, a player who wins,
    a possible choice and an amount the winner can pay. Rules that depend on the format are checked before this."""
    if trade.finished:
        raise TradeError(f"The trade of game {trade.game} is finished.")
    _heroes_first(trade)
    expected = expected_report_section(trade)
    if report.section != expected:
        raise TradeError(f"The {expected.replace('_', ' ')} is expected now.")
    if report.winner not in trade.players:
        raise TradeError("The winner must be one of the two players of this match.")
    if report.section == "town_bid" and report.choice not in trade.towns:
        raise TradeError("The town chosen must be one of the pair.")
    if report.section == "pack_bid" and report.choice not in PACKS:
        raise TradeError("The pack chosen must be pack1 or pack2.")
    if report.section == "first_choice_bid" and report.choice not in FIRST_CHOICES:
        raise TradeError("The first choice is the hero or the color.")
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
    _heroes_first(trade)
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
    elif expected == "first_choice_bid":
        if typed not in FIRST_CHOICES:
            raise TradeError("This bid is for who chooses first. Choose hero or color.")
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


# --- heroes: the bans and the draw --------------------------------------------------------------------------------


def hero_pool(trade: Trade, heroes: Catalogue, templates: Catalogue) -> dict[str, tuple[str, ...]]:
    """The heroes that can still be drawn in each town of the game, as ids: the heroes the template's map offers, less
    the ones the players banned."""
    return hero_pool_of(heroes, templates.find(trade.template), trade.towns, set(trade.banned_heroes))


def _heroes_needed(trade: Trade, town: str) -> int:
    """How many heroes of a town the draw needs: two for a mirror, one for each town of a pair."""
    return 2 if trade.mirror else 1


def _hero_names(heroes: Catalogue, ids) -> str:
    return ", ".join(heroes.find(hero).name for hero in ids)


def check_hero_ban(trade: Trade, ban: HeroBan, heroes: Catalogue, templates: Catalogue) -> None:
    """Raise TradeError unless `ban` fits the trade: the ban section is open, it is this player's turn, no more heroes
    than allowed, each of them one that can be drawn, and enough heroes left for the draw."""
    if trade.section != "hero_bans":
        raise TradeError("Heroes cannot be banned now.")
    if ban.player not in trade.players:
        raise TradeError("Only one of the two players of this game can ban heroes.")
    if ban.player != trade.ban_turn:
        raise TradeError("It is the other player's turn to ban heroes.")
    limit = trade.kind.hero_bans
    if len(ban.heroes) > limit:
        raise TradeError(f"At most {limit} hero{'' if limit == 1 else 'es'} may be banned.")
    if len(set(ban.heroes)) != len(ban.heroes):
        raise TradeError("A hero can only be banned once.")
    pool = hero_pool(trade, heroes, templates)
    can_be_banned = {hero for ids in pool.values() for hero in ids}
    for hero in ban.heroes:
        if hero not in can_be_banned:
            raise TradeError(
                f"{heroes.find(hero).name if heroes.find(hero) else hero} cannot be banned: only heroes that can be drawn "
                "for this game can be, that is the heroes of the drawn town(s) that the template's map offers."
            )
    for town, ids in pool.items():
        left = len([hero for hero in ids if hero not in ban.heroes])
        if left < _heroes_needed(trade, town):
            raise TradeError("Too few heroes would be left to draw from, so nobody banned anyone.")


def make_hero_ban(trade: Trade, heroes: Catalogue, templates: Catalogue, player: int, hero_texts: list[str]) -> HeroBan:
    """A player's hero ban from the heroes they named, checked, with a message that says what is wrong."""
    ids = []
    for text in hero_texts:
        hero = heroes.find(text)
        if hero is None:
            raise TradeError(f"{text!r} is not a hero. Heroes are named as in data/heroes.json, for example Orrin.")
        if hero.id not in ids:  # naming a hero twice bans it once
            ids.append(hero.id)
    ban = HeroBan(player, tuple(ids))
    check_hero_ban(trade, ban, heroes, templates)
    return ban


def draw_heroes(trade: Trade, heroes: Catalogue, templates: Catalogue, random_source: random.Random | None = None) -> tuple[str, ...]:
    """The heroes of the game: two different heroes of the town for a mirror, one hero of each town of the pair
    otherwise (in the order of the towns), from the heroes that can be drawn. Raises TradeError when there are too few."""
    return pick_heroes(trade.towns, trade.mirror, hero_pool(trade, heroes, templates), random_source)


def check_heroes_drawn(trade: Trade, drawn: tuple[str, ...], heroes: Catalogue, templates: Catalogue) -> None:
    """Raise TradeError unless `drawn` is what the bot may draw now: right after the bans (or the rolls), and heroes
    that can be drawn, one of each town of a pair or two different ones of the town of a mirror."""
    if trade.section != "hero_draw":
        raise TradeError("The heroes cannot be drawn now.")
    check_heroes_fit(trade.towns, trade.mirror, drawn, hero_pool(trade, heroes, templates))


def make_heroes_drawn(
    trade: Trade, heroes: Catalogue, templates: Catalogue, random_source: random.Random | None = None
) -> tuple[str, ...]:
    """Draw the heroes of a game that is due for the draw, and check the draw."""
    if trade.section != "hero_draw":
        raise TradeError("The heroes cannot be drawn now.")
    drawn = draw_heroes(trade, heroes, templates, random_source)
    check_heroes_drawn(trade, drawn, heroes, templates)
    return drawn


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
    heroes: Catalogue | None = None,
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

    hero_catalogue = heroes if heroes is not None else Catalogue([])

    def hero_ids(words) -> tuple[str, ...]:
        return tuple(hero_catalogue.find(w).id if hero_catalogue.find(w) else w for w in words)

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
                draw = Draw(ids(record.data["towns"]), ids(record.data.get("packs", ())), hero_ids(record.data.get("heroes", ())))
                check_start(draw, kind, mirror, allowed_towns, hero_catalogue, templates.find(template))
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
                    draw = Draw(ids(record.data["towns"]), ids(record.data.get("packs", ())), hero_ids(record.data.get("heroes", ())))
                    roll = Roll(record.data["player"], ids(record.data["bans"]), draw)
                    check_roll(trade, roll, allowed_towns, hero_catalogue, templates)
                    trades[game] = trade.with_roll(roll)
                elif record.type == "roll_skipped":
                    make_skip(trade, record.data["player"])
                    trades[game] = trade.with_skip(record.data["player"])
                elif record.type == "hero_bans":
                    ban = HeroBan(record.data["player"], hero_ids(record.data["heroes"]))
                    check_hero_ban(trade, ban, hero_catalogue, templates)
                    trades[game] = trade.with_hero_ban(ban)
                elif record.type == "heroes_drawn":
                    drawn = hero_ids(record.data["heroes"])
                    check_heroes_drawn(trade, drawn, hero_catalogue, templates)
                    trades[game] = trade.with_heroes(drawn)
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
    return f"{'+' if amount > 0 else '-'}{spaced(abs(amount))}" if amount else "0"


def _starting_gold_line(trade: Trade) -> str:
    return f"Starting gold: {spaced(trade.start_gold)}"


def _difference_line(trade: Trade, mentions: dict[int, str]) -> str:
    gold = trade.gold
    a, b = trade.players
    return f"Gold difference: {mentions[a]} {signed(gold[a] - trade.start_gold)}, {mentions[b]} {signed(gold[b] - trade.start_gold)}"


def _pair_words(towns: Catalogue, played: tuple[str, ...]) -> str:
    """The town(s) the players play, by name in `quotes`, which is how they are read back: "`Castle` vs `Tower`"."""
    return " vs ".join(f"`{towns.find(town).name}`" for town in played)


def pack_lines(towns: Catalogue, packs: tuple[str, ...]) -> list[str]:
    """The two packs, one line each, for prompts: "Pack1: Castle, Tower, Cove"."""
    draw = Draw((), packs)
    return [
        f"{name.capitalize()}: {', '.join(towns.find(t).name for t in draw.pack(number))}" for number, name in enumerate(PACKS)
    ]


def _hero_line(mirror: bool, towns: Catalogue, heroes: Catalogue, hero_id: str, town: str) -> str:
    """One hero with a link to the page of the hero. In a game with two towns the town of the hero is said too. The name
    is in `quotes`, which is how it is read back; the link is not, and has no preview."""
    hero = heroes.find(hero_id)
    place = "" if mirror else f" ({towns.find(town).name})"
    return f"`{hero.name}`{place} <{hero.details['link']}>"


def _draw_lines(trade: Trade, towns: Catalogue, draw: Draw, heroes: Catalogue | None = None) -> list[str]:
    """What was drawn, one line each, for the record of a trade starting (and of a roll that draws packs). The marker
    words ("Pair:", "Town:", "Pack1:") are how `state.py` finds the towns again; the layout is only for the eyes:

        Pair: `Castle` vs `Tower`
        Pack1: `Rampart`, `Inferno`, `Dungeon`
        Pack2: ...
        Hero1: `Orrin` (Castle) <https://heroes.thelazy.net/index.php/Orrin>
        Hero2: ...
    """
    lines = [f"{'Town' if trade.mirror else 'Pair'}: {_pair_words(towns, draw.towns)}"]
    if draw.packs:
        for number, name in enumerate(PACKS):
            members = ", ".join(f"`{towns.find(t).name}`" for t in draw.pack(number))
            lines.append(f"{name.capitalize()}: {members}")
    if draw.heroes and heroes is not None:  # a roulette that draws its heroes together with the towns
        for number, hero_id in enumerate(draw.heroes):
            lines.append(f"Hero{number + 1}: {_hero_line(trade.mirror, towns, heroes, hero_id, draw.towns[number % len(draw.towns)])}")
    return lines


def _named(towns: Catalogue, ids: tuple[str, ...]) -> tuple[str, ...]:
    """Town ids as the thread quotes them: by name."""
    return tuple(towns.find(town).name for town in ids)


def _draw_data(towns: Catalogue, draw: Draw, heroes: Catalogue | None) -> dict:
    """The towns, packs and heroes of a draw as the thread quotes them: by name."""
    return {
        "towns": _named(towns, draw.towns),
        **({"packs": _named(towns, draw.packs)} if draw.packs else {}),
        **({"heroes": tuple(heroes.find(hero).name for hero in draw.heroes)} if draw.heroes and heroes is not None else {}),
    }


def start_data(trade: Trade, towns: Catalogue, heroes: Catalogue | None = None) -> dict:
    """The data of the record posted when a trade starts: the words `opening_line` quotes."""
    return _draw_data(towns, trade.first_draw, heroes)


def roll_data(roll: Roll, towns: Catalogue, heroes: Catalogue | None = None) -> dict:
    """The data of the record posted for a roll: the words `roll_line` quotes."""
    return {"player": roll.player, "bans": _named(towns, roll.bans), **_draw_data(towns, roll.draw, heroes)}


def report_data(report: Report, towns: Catalogue) -> dict:
    """The data of the record posted for a report: the words `report_line` quotes."""
    choice = towns.find(report.choice).name if report.section == "town_bid" else report.choice
    return {
        "reporter": report.reporter,
        "winner": report.winner,
        "amount": report.amount,
        SECTION_TABLE[report.section].choice_field: choice,
    }


def hero_bans_data(ban: HeroBan, heroes: Catalogue) -> dict:
    """The data of the record posted for a hero ban: the words `hero_bans_line` quotes."""
    return {"player": ban.player, "heroes": tuple(heroes.find(hero).name for hero in ban.heroes)}


def heroes_drawn_data(drawn: tuple[str, ...], heroes: Catalogue) -> dict:
    """The data of the record posted for the draw: the words `heroes_drawn_line` quotes."""
    return {"heroes": tuple(heroes.find(hero).name for hero in drawn)}


def opening_line(
    trade: Trade, resumed: bool, mentions: dict[int, str], towns: Catalogue, templates: Catalogue, heroes: Catalogue | None = None
) -> str:
    """The text of the record posted when a trade is opened for the first time or reopened: the game, what was drawn,
    and the starting gold (or, when reopened, the difference so far). How the trade is run was said when the match started.

    The first two `quoted` words are the town ids of the pair, which is how the pair is read back
    (when reopened, it is the pair that stands now).
    """
    name = templates.find(trade.template).name
    gold = _difference_line(trade, mentions) if resumed else _starting_gold_line(trade)
    draw = trade.draw if resumed else trade.first_draw
    lines = [f"Game {trade.game} ({name})" + (": the trade continues" if resumed else ""), *_draw_lines(trade, towns, draw, heroes)]
    if resumed and trade.heroes_after_rolls and trade.drawn_heroes and heroes is not None:
        lines += _hero_lines(trade, towns, heroes, trade.drawn_heroes)
    return "\n".join([*lines, gold])


def _rolls_left_line(trade: Trade, mentions: dict[int, str], player: int) -> str:
    """How many rolls a player has left, and why they cannot use one now, if they cannot."""
    left = max(0, trade.rules.rolls_per_player - trade.rolls_used(player))
    notes = []
    if left and player in trade.skipped:
        notes.append("skipped")
    elif left and trade.gold[player] < trade.rules.roll_cost:
        notes.append("not enough gold")
    return f"{mentions[player]}: {left} roll{'' if left == 1 else 's'} left" + (f" ({', '.join(notes)})" if notes else "")


def _standing_lines(trade: Trade, towns: Catalogue, heroes: Catalogue | None) -> list[str]:
    """What stands, in plain words, for a prompt after an undo: the town(s), the packs and the heroes drawn with them."""
    lines = [f"{'Town' if trade.mirror else 'Pair'}: {pair_names(towns, trade.towns)}"]
    if trade.packs:
        lines += pack_lines(towns, trade.packs)
    if heroes is not None:
        for number, hero_id in enumerate(trade.draw.heroes):
            place = "" if trade.mirror else f" ({towns.find(trade.towns[number]).name})"
            lines.append(f"Hero{number + 1}: {heroes.find(hero_id).name}{place}")
    return lines


def prompt(
    trade: Trade, mentions: dict[int, str], towns: Catalogue, show_draw: bool = True, heroes: Catalogue | None = None
) -> str:
    """What to do next in an unfinished trade: "Next step: ..." and a few short lines. The first player (A) bids first
    in every game; this is a provisional rule.

    The roll section says what stands only when `show_draw` is true. The message that drew it (the start of the trade,
    a roll) is right above the prompt, so repeating it would only say it twice; after an undo it is not.
    """
    if trade.section == "town_roll":
        rules = trade.rules
        bans = "it bans this town" if trade.mirror else f"banning up to {_count_towns(rules.max_roll_bans)} of the pair"
        return "\n".join(
            [
                "Next step: town roll",
                *(_standing_lines(trade, towns, heroes) if show_draw else []),
                f"Cost: {spaced(rules.roll_cost)} gold",
                *(_rolls_left_line(trade, mentions, player) for player in trade.players),
                f"Roll with /trade roll ({bans}); skip with /trade skip-roll",
            ]
        )
    if trade.section == "hero_bans":
        limit = trade.kind.hero_bans
        return "\n".join(
            [
                "Next step: hero bans",
                f"{mentions[trade.ban_turn]} may ban up to {limit} hero{'' if limit == 1 else 'es'} of {pair_names(towns, trade.towns)}",
                "Ban with /trade ban-heroes; ban nobody by sending it without a hero",
            ]
        )
    if trade.section == "hero_draw":
        return "The heroes are being drawn."
    raise_by = f"{mentions[trade.players[0]]} bids first, raising by at least {GOLD_STEP}"
    if trade.section == "town_bid":
        lines = [f"Next step: town bid: {pair_names(towns, trade.towns)}", raise_by, "Report the result with /trade report"]
    elif trade.section == "first_choice_bid":
        lines = [
            "Next step: bid for the first choice",
            raise_by,
            "Its winner chooses first either the hero or the color, and the other player chooses the other",
            "Report the result with /trade report, choosing hero or color",
        ]
    elif trade.section == "pack_bid":
        lines = [
            "Next step: pack bid",
            *pack_lines(towns, trade.packs),
            raise_by,
            "Report the result with /trade report, choosing pack1 or pack2",
        ]
    else:
        lines = ["Next step: color bid", raise_by, "Report the result with /trade report, choosing red or blue"]
    return "\n".join(lines)


def roll_line(trade: Trade, roll: Roll, mentions: dict[int, str], towns: Catalogue, heroes: Catalogue | None = None) -> str:
    """The text of the record posted for a roll; `trade` is the trade including the roll.

    The first mention is the roller; the `quoted` words before "New pair:" (or "New town:") are the banned towns, the
    ones after it the new town(s), and then the packs.
    """
    roller, other = mentions[roll.player], mentions[trade.other(roll.player)]
    bans = ", ".join(f"`{towns.find(t).name}`" for t in roll.bans)
    banning = f"rolled, banning {bans}," if roll.bans else "rolled without banning a town,"
    paid = f"Game {trade.game} - {roller} {banning} and paid {spaced(trade.rules.roll_cost)} gold to {other}."
    drawn = _draw_lines(trade, towns, roll.draw, heroes)
    drawn[0] = ("New town:" if trade.mirror else "New pair:") + drawn[0].split(":", 1)[1]
    return "\n".join([paid, *drawn, _difference_line(trade, mentions)])


def hero_bans_line(trade: Trade, ban: HeroBan, mentions: dict[int, str], heroes: Catalogue) -> str:
    """The text of the record posted for a player's hero bans. The first mention is the player, the `quoted` words the
    banned heroes."""
    banned = ", ".join(f"`{heroes.find(hero).name}`" for hero in ban.heroes)
    return f"Game {trade.game} - {mentions[ban.player]} bans {banned if ban.heroes else 'no hero'}."


def _hero_lines(trade: Trade, towns: Catalogue, heroes: Catalogue, drawn: tuple[str, ...]) -> list[str]:
    """The drawn heroes, a line each, with a link to the page of the hero. In a game with two towns the town of each
    hero is said too. The name is in `quotes`, which is how it is read back; the link is not, and has no preview."""
    lines = []
    for number, hero_id in enumerate(drawn):
        lines.append(_hero_line(trade.mirror, towns, heroes, hero_id, trade.towns[number % len(trade.towns)]))
    return lines


def heroes_drawn_line(trade: Trade, drawn: tuple[str, ...], towns: Catalogue, heroes: Catalogue) -> str:
    """The text of the record posted when the heroes are drawn: the `quoted` words are the heroes, in order."""
    return "\n".join([f"Game {trade.game} - The heroes are drawn:", *_hero_lines(trade, towns, heroes, drawn)])


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
    won = f"{winner} won at `{spaced(report.amount)}` gold and"
    if report.section == "town_bid":
        town = towns.find(report.choice)
        other = towns.find(next(t for t in trade.towns if t != report.choice)).name
        what, lines = "Town bid", [f"{won} plays `{town.name}`", f"{loser} plays {other}"]
    elif report.section == "pack_bid":
        other = PACKS[1 - PACKS.index(report.choice)]
        what, lines = "Pack bid", [f"{won} takes `{report.choice}`", f"{loser} gets {other}"]
    elif report.section == "first_choice_bid":
        if report.choice == "hero":
            lines = [f"{winner} won at `{spaced(report.amount)}` gold and chooses the `hero` first", f"{loser} then chooses the color and plays the other hero"]
        else:
            lines = [f"{winner} won at `{spaced(report.amount)}` gold and chooses the `color` first", f"{loser} then chooses a hero and plays the other color"]
        what = "Bid for the first choice"
    else:
        other = "blue" if report.choice == "red" else "red"
        what, lines = "Color bid", [f"{won} plays `{report.choice}`", f"{loser} plays {other}"]
    return "\n".join([f"Game {trade.game} - {what}, reported by {reporter}", *lines, _difference_line(trade, mentions)])


def _first_choice_summary(
    trade: Trade, report: Report, mentions: dict[int, str], towns: Catalogue, templates: Catalogue, lobby, heroes: Catalogue | None
) -> str:
    """The lobby settings of a mirror roulette: the town, the two heroes, and who chooses what. The bot does not track
    which hero or color is taken, so there are no colors, only who chooses what and the gold difference."""
    gold = trade.gold
    winner, loser = report.winner, trade.other(report.winner)
    if report.choice == "hero":
        says = {winner: "chooses the hero first (one of the two), gets the other color", loser: "chooses the color, plays the other hero"}
    else:
        says = {winner: "chooses the color, plays the other hero", loser: "chooses the hero first (one of the two), plays the other color"}
    lines = [f"Game {trade.game} lobby settings - {templates.find(trade.template).name}", *lobby]
    lines.append(f"Town (both players): {towns.find(trade.towns[0]).name}")
    if trade.heroes and heroes is not None:
        lines.append(f"Heroes: {' and '.join(heroes.find(hero).name for hero in trade.heroes)}")
    for player in trade.players:
        lines.append(f"{mentions[player]}: {says[player]}, gold {signed(gold[player] - trade.start_gold)}")
    return "\n".join(lines)


def summary(
    trade: Trade,
    mentions: dict[int, str],
    towns: Catalogue,
    templates: Catalogue,
    lobby: list[str] | tuple = (),
    heroes: Catalogue | None = None,
) -> str:
    """The lobby settings of a finished trade: the settings typed into the lobby (`lobby`, one line each, when they are
    stated), then each player's town (and, in a roulette, hero), color and gold difference, the red player first."""
    reports = {report.section: report for report in trade.reports}
    if "first_choice_bid" in reports:
        return _first_choice_summary(trade, reports["first_choice_bid"], mentions, towns, templates, lobby, heroes)
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
    for player in sorted(trade.players, key=lambda p: plays_color[p] != "red"):  # red is listed first
        parts = []
        if player in plays_town:
            town = towns.find(plays_town[player]).name
            if trade.heroes and heroes is not None and not trade.mirror:  # the hero drawn for the town they play
                town += f" ({heroes.find(trade.heroes[trade.towns.index(plays_town[player])]).name})"
            parts.append(town)
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
    if trade.section in ("hero_bans", "hero_draw"):
        return f", next: {trade.section.replace('_', ' ')}"
    bid = trade.bids[len(trade.reports)]
    rolls = " (rolls still open)" if trade.section == "town_roll" else ""
    if bid == "town_bid":
        return f", next: town bid {pair_names(towns, trade.towns)}{rolls}"
    words = {"first_choice_bid": "bid for the first choice"}.get(bid, bid.replace("_", " "))
    return f", next: {words}{rolls}"


def next_message(
    trade: Trade,
    mentions: dict[int, str],
    towns: Catalogue,
    templates: Catalogue,
    lobby: list[str] | tuple = (),
    show_draw: bool = True,
    heroes: Catalogue | None = None,
) -> str:
    """What the thread says after the trade moved on: what to do next, or the lobby settings when it is done."""
    if trade.finished:
        return summary(trade, mentions, towns, templates, lobby, heroes)
    return prompt(trade, mentions, towns, show_draw, heroes)
