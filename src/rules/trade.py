"""The trade before each game: faction roll, bids for faction and color, and the lobby settings.

The bot guides the players through the sections of a game's trade and keeps the gold.
Players bid between themselves in the thread and report the results; the bot draws
the random faction pairs and the 200% color toss itself. Everything here is plain
Python on a `Match` (see state.py): each function checks a player's request and
returns an `Action`, the event to post, its text and who to notify.
"""

import random
from dataclasses import dataclass, field, replace

from rules.catalogue import Catalogue
from rules.errors import UserError
from rules.formats import TradeSettings, trade_settings
from rules.ledger import Ledger
from rules.selection import Game, games
from state import UNDOABLE, Event, Match

COLORS = ("red", "blue")
MIN_RAISE = 100
# Open question: who bids first in games after the first. Provisional: A, every game.
FIRST_BIDDER = "A"

_SYSTEM_RANDOM = random.SystemRandom()


class TradeError(UserError):
    """A trade request cannot be accepted. The message is shown to the player."""


@dataclass(frozen=True)
class Action:
    """What to post after an accepted request."""

    type: str  # event type
    data: dict  # event data
    text: str
    ping: tuple[int, ...] = ()  # users who have to act next


@dataclass
class TradeState:
    number: int
    game: Game
    settings: TradeSettings
    players: tuple[int, int]  # (A, B)
    ledger: Ledger
    events: list[Event]
    started: bool = False
    pair: tuple[str, str] | None = None
    banned: tuple[str, ...] = ()
    rolls_used: dict = field(default_factory=dict)
    declined: set = field(default_factory=set)
    rolls_closed: bool = False  # a faction bid was reported, so open rolls are skipped
    factions: dict = field(default_factory=dict)  # user -> faction id
    colors: dict = field(default_factory=dict)  # user -> "red" | "blue"
    toss_winner: int | None = None
    section: str | None = None  # the section the players are in; None when finished

    @property
    def complete(self) -> bool:
        return self.started and self.section is None

    @property
    def gold(self) -> dict:
        return self.ledger.gold

    def eligible_rollers(self) -> list[int]:
        cost = self.settings.roll_cost
        return [
            p
            for p in self.players
            if p not in self.declined
            and self.rolls_used.get(p, 0) < self.settings.rolls_per_player
            and self.gold[p] >= cost
        ]

    @property
    def first_bidder(self) -> int:
        return self.players[0] if FIRST_BIDDER == "A" else self.players[1]


def draw_pair(allowed: tuple[str, ...], banned: tuple[str, ...], rng: random.Random = _SYSTEM_RANDOM) -> tuple[str, str]:
    """Two different factions, chosen at random from the allowed ones that are not banned."""
    pool = [f for f in allowed if f not in banned]
    if len(pool) < 2:
        raise TradeError("Fewer than two factions would be left after those bans, so this roll is not possible.")
    first, second = rng.sample(pool, 2)
    return first, second


def _other_color(color: str) -> str:
    return COLORS[1] if color == COLORS[0] else COLORS[0]


def _other_in_pair(pair: tuple[str, str], faction: str) -> str:
    return pair[1] if faction == pair[0] else pair[0]


# --- reading the state -----------------------------------------------------


def _game(match: Match, number: int) -> Game:
    all_games = games(match)
    if not 1 <= number <= len(all_games):
        raise TradeError(f"There is no game {number}; this match has {len(all_games)}.")
    return all_games[number - 1]


def trade_state(match: Match, number: int) -> TradeState:
    """Rebuild the trade of one game from its events."""
    game = _game(match, number)
    settings = trade_settings(match.phase, game.template)
    players = (match.a, match.b)
    events = list(match.trade.get(number, []))
    st = TradeState(number, game, settings, players, Ledger(players, settings.starting_gold), events)
    st.rolls_used = {p: 0 for p in players}

    for e in events:
        d = e.data
        st.started = True
        if e.type == "pair_drawn":
            st.pair = tuple(d["pair"])
        elif e.type == "roll":
            st.rolls_used[d["by"]] += 1
            st.ledger.pay(d["by"], settings.roll_cost)
            st.banned += tuple(d["bans"])
            st.pair = tuple(d["pair"])
        elif e.type == "decline":
            st.declined.add(d["by"])
        elif e.type == "faction_bid":
            st.rolls_closed = True
            st.ledger.pay(d["winner"], d["amount"])
            st.factions[d["winner"]] = d["faction"]
            st.factions[st.ledger.other(d["winner"])] = _other_in_pair(st.pair, d["faction"])
        elif e.type == "color_bid":
            st.ledger.pay(d["winner"], d["amount"])
            st.colors[d["winner"]] = d["color"]
            st.colors[st.ledger.other(d["winner"])] = _other_color(d["color"])
        elif e.type == "color_toss":
            st.toss_winner = d["winner"]
        elif e.type == "color_choice":
            st.colors[d["by"]] = d["color"]
            st.colors[st.ledger.other(d["by"])] = _other_color(d["color"])

    if st.started:
        st.section = next((s for s in settings.sections if not _section_done(st, s)), None)
    return st


def _section_done(st: TradeState, section: str) -> bool:
    if section == "faction_roll":
        return st.rolls_closed or not st.eligible_rollers()
    if section == "faction_bid":
        return bool(st.factions)
    return bool(st.colors)  # color_bid and color_toss both end with the colors known


def first_unfinished(match: Match) -> int | None:
    for game in games(match):
        if not trade_state(match, game.number).complete:
            return game.number
    return None


def choose_game(match: Match, requested: int | None) -> int:
    """The game a trade command applies to: the one named, or the first unfinished."""
    if requested is not None:
        _game(match, requested)
        return requested
    number = first_unfinished(match)
    if number is None:
        raise TradeError("Every trade of this match is finished.")
    return number


def first_unstarted(match: Match) -> int | None:
    return next((g.number for g in games(match) if not trade_state(match, g.number).started), None)


def latest_game(match: Match) -> int | None:
    """The game whose trade was posted to most recently (where an undo usually applies)."""
    latest = [(events[-1].n, number) for number, events in match.trade.items() if events]
    return max(latest)[1] if latest else None


def following_game(match: Match, number: int) -> int | None:
    """The game after `number` if it exists and its trade has not started."""
    if number >= len(games(match)):
        return None
    return None if trade_state(match, number + 1).started else number + 1


def after(match: Match, number: int, type_: str, data: dict) -> Match:
    """The match as it will be once an event is posted (used to write the message)."""
    events = list(match.trade.get(number, []))
    if type_ == "undo":
        if events and events[-1].type in UNDOABLE:
            events.pop()
    else:
        events.append(Event(0, type_, data))
    return replace(match, trade={**match.trade, number: events})


# --- texts -----------------------------------------------------------------


def _mention(user: int) -> str:
    return f"<@{user}>"


def _pair_text(st: TradeState, factions: Catalogue) -> str:
    return f"{factions.name_of(st.pair[0])} vs {factions.name_of(st.pair[1])}"


def _gold_text(st: TradeState) -> str:
    a, b = st.players
    return f"Gold: {_mention(a)} {st.gold[a]}, {_mention(b)} {st.gold[b]}"


def _header(st: TradeState) -> str:
    s = st.settings
    gold = f", {s.starting_gold} gold each" if s.starting_gold else ""
    return f"**Game {st.number}: {st.game.template}** ({s.difficulty}%{gold})"


def _roll_eligibility_text(st: TradeState) -> str:
    eligible = st.eligible_rollers()
    if len(eligible) == 2:
        return "Both players may roll"
    return f"{_mention(eligible[0])} may roll"


def _prompt(st: TradeState, factions: Catalogue) -> str:
    """The instruction for the section the players are in."""
    s = st.settings
    if st.section == "faction_roll":
        return (
            f"{_pair_text(st, factions)}. A roll costs {s.roll_cost} gold. {_roll_eligibility_text(st)}. "
            f"Use `/trade roll` (you may ban up to {s.max_roll_bans} of these factions) or `/trade decline`. "
            "If you do not want to roll, just bid for the faction and report it with `/trade report`."
        )
    if st.section == "faction_bid":
        return (
            f"Bid for the faction: {_pair_text(st, factions)}. {_mention(st.first_bidder)} starts, "
            f"minimum raise {MIN_RAISE}. When the bidding is done, report it with "
            "`/trade report winner amount choice` (choice = the faction)."
        )
    if st.section == "color_bid":
        return (
            f"Bid for the color. {_mention(st.first_bidder)} starts, minimum raise {MIN_RAISE}. "
            "Report it with `/trade report winner amount choice` (choice = red or blue). Red moves first."
        )
    if st.section == "color_toss":
        return (
            f"{_mention(st.toss_winner)} won the toss for color. "
            "They choose with `/trade report choice` (red or blue). Red moves first."
        )
    return summary_text(st, factions)


def summary_text(st: TradeState, factions: Catalogue) -> str:
    """The lobby settings of a finished trade."""
    lines = [f"**Lobby settings, game {st.number}**", f"Template: **{st.game.template}** ({st.settings.difficulty}%)"]
    all_random = not st.factions
    for p in st.players:
        parts = [] if all_random else [factions.name_of(st.factions[p])]
        parts.append(st.colors[p])
        if not all_random:
            parts.append(f"{st.gold[p]} gold")
        lines.append(f"{_mention(p)}: {', '.join(parts)}")
    if all_random:
        lines.append("Factions: assigned by the game (all random).")
    red = next(p for p in st.players if st.colors[p] == "red")
    lines.append(f"Red moves first: {_mention(red)}.")
    return "\n".join(lines)


def _who_to_notify(st: TradeState) -> tuple[int, ...]:
    if st.section == "faction_roll":
        return tuple(st.eligible_rollers())
    if st.section in ("faction_bid", "color_bid"):
        return (st.first_bidder,)
    if st.section == "color_toss":
        return (st.toss_winner,)
    return ()


def _action(match: Match, number: int, type_: str, data: dict, lead: str, factions: Catalogue, with_header=False) -> Action:
    """Build the Action: a lead sentence, then the state after the event."""
    st = trade_state(after(match, number, type_, data), number)
    lines = [_header(st)] if with_header else []
    if lead:
        lines.append(lead)
    lines.append(_prompt(st, factions))
    if st.settings.starting_gold and not st.complete:
        lines.append(_gold_text(st))
    return Action(type_, data, "\n".join(lines), _who_to_notify(st))


# --- requests --------------------------------------------------------------


def _require_active(st: TradeState) -> None:
    if not st.started:
        raise TradeError(f"The trade of game {st.number} has not started. Use `/trade start` first.")
    if st.complete:
        raise TradeError(f"The trade of game {st.number} is finished. Use `/trade undo` to correct the last report.")


def start_trade(match: Match, number: int, factions: Catalogue, rng: random.Random = _SYSTEM_RANDOM) -> Action:
    """Start the trade of a game: the bot draws the first pair (or, at 200%, the color toss)."""
    st = trade_state(match, number)
    if st.started:
        raise TradeError(f"The trade of game {number} has already started.")
    if "color_toss" in st.settings.sections:
        winner = match.a if rng.randrange(2) == 0 else match.b
        type_, data = "color_toss", {"game": number, "winner": winner}
    else:
        pair = draw_pair(match.phase.allowed_factions, (), rng)
        type_, data = "pair_drawn", {"game": number, "pair": list(pair)}
    return _action(match, number, type_, data, "", factions, with_header=True)


def _resolve_faction(text: str, factions: Catalogue, allowed: tuple[str, ...]) -> str:
    entry = factions.find(text)
    if entry is None or entry.id not in allowed:
        names = ", ".join(factions.name_of(f) for f in allowed)
        raise TradeError(f"{text!r} is not an allowed faction here. Allowed: {names}.")
    return entry.id


def roll(match: Match, number: int, user: int, ban_texts: list[str], factions: Catalogue, rng=_SYSTEM_RANDOM) -> Action:
    """A player rolls the pair: pays the cost, bans some of the current pair, and the bot draws a new pair."""
    st = trade_state(match, number)
    _require_active(st)
    if st.section != "faction_roll":
        raise TradeError("The roll is over; the bidding has started.")
    s = st.settings
    if user in st.declined:
        raise TradeError("You declined to roll.")
    if st.rolls_used[user] >= s.rolls_per_player:
        raise TradeError("You have no roll left.")
    if st.gold[user] < s.roll_cost:
        raise TradeError(f"A roll costs {s.roll_cost} gold and you have {st.gold[user]}.")

    if len(ban_texts) > s.max_roll_bans:
        raise TradeError(f"You can ban at most {s.max_roll_bans} faction(s) per roll.")
    bans = []
    for text in ban_texts:
        faction = _resolve_faction(text, factions, match.phase.allowed_factions)
        if faction not in st.pair:
            raise TradeError(f"{factions.name_of(faction)} is not in the current pair ({_pair_text(st, factions)}).")
        if faction not in bans:
            bans.append(faction)

    new_pair = draw_pair(match.phase.allowed_factions, st.banned + tuple(bans), rng)
    data = {"game": number, "by": user, "bans": bans, "pair": list(new_pair)}
    banning = f", banning {', '.join(factions.name_of(b) for b in bans)}" if bans else ""
    lead = f"{_mention(user)} rolled{banning} and paid {s.roll_cost} gold to {_mention(st.ledger.other(user))}."
    return _action(match, number, "roll", data, lead, factions)


def decline(match: Match, number: int, user: int, factions: Catalogue) -> Action:
    st = trade_state(match, number)
    _require_active(st)
    if st.section != "faction_roll":
        raise TradeError("The roll is over; the bidding has started.")
    if user not in st.eligible_rollers():
        raise TradeError("You cannot roll anyway, so there is nothing to decline.")
    data = {"game": number, "by": user}
    return _action(match, number, "decline", data, f"{_mention(user)} does not want to roll.", factions)


def _resolve_color(text: str) -> str:
    color = text.strip().lower()
    if color not in COLORS:
        raise TradeError("The color must be red or blue.")
    return color


def report(
    match: Match,
    number: int,
    user: int,
    choice: str,
    winner: int | None,
    amount: int | None,
    factions: Catalogue,
) -> Action:
    """A player reports the result of the current bid (or, at 200%, the color chosen after the toss)."""
    st = trade_state(match, number)
    _require_active(st)

    if st.section == "color_toss":
        if user != st.toss_winner:
            raise TradeError(f"Only {_mention(st.toss_winner)}, who won the toss, chooses the color.")
        color = _resolve_color(choice)
        data = {"game": number, "by": user, "color": color}
        lead = f"{_mention(user)} chose **{color}**."
        return _action(match, number, "color_choice", data, lead, factions)

    if winner is None or winner not in st.players:
        raise TradeError("Say who won the bid: `winner` must be one of the two players.")
    if amount is None:
        raise TradeError("Say how much the winner pays: `amount`.")
    if not st.ledger.can_pay(winner, amount):
        if amount < 0:
            raise TradeError("The amount must be 0 or more.")
        raise TradeError(f"{_mention(winner)} has only {st.gold[winner]} gold, not {amount}.")
    loser = st.ledger.other(winner)

    if st.section in ("faction_roll", "faction_bid"):
        if choice.strip().lower() in COLORS:
            raise TradeError(f"The faction bid comes first. Report the faction: {_pair_text(st, factions)}.")
        faction = _resolve_faction(choice, factions, match.phase.allowed_factions)
        if faction not in st.pair:
            raise TradeError(f"{factions.name_of(faction)} is not in the pair: {_pair_text(st, factions)}.")
        data = {"game": number, "by": user, "winner": winner, "amount": amount, "faction": faction}
        skipped = "The open rolls were skipped.\n" if st.section == "faction_roll" else ""
        lead = (
            f"{skipped}{_mention(winner)} won the faction bid at {amount} gold and chose "
            f"**{factions.name_of(faction)}**; {_mention(loser)} plays {factions.name_of(_other_in_pair(st.pair, faction))}."
        )
        return _action(match, number, "faction_bid", data, lead, factions)

    # color_bid
    if choice.strip().lower() not in COLORS:
        raise TradeError("The faction is settled. Now report the color: red or blue.")
    color = _resolve_color(choice)
    data = {"game": number, "by": user, "winner": winner, "amount": amount, "color": color}
    lead = (
        f"{_mention(winner)} won the color bid at {amount} gold and takes **{color}**; "
        f"{_mention(loser)} plays {_other_color(color)}."
    )
    return _action(match, number, "color_bid", data, lead, factions)


def undo(match: Match, number: int, user: int, factions: Catalogue) -> Action:
    """Undo the latest player report. Random results and rolls are final."""
    st = trade_state(match, number)
    if not st.started or len(st.events) == 1 and st.events[0].type in ("pair_drawn", "color_toss"):
        raise TradeError(f"There is nothing to undo in game {number}.")
    if st.events[-1].type not in UNDOABLE:
        raise TradeError(
            "Random results are final: a roll cannot be undone, otherwise anyone could roll again for a better pair."
        )
    data = {"game": number, "by": user}
    return _action(match, number, "undo", data, f"{_mention(user)} undid the last report.", factions)


def status_text(match: Match, number: int, factions: Catalogue) -> str:
    st = trade_state(match, number)
    if not st.started:
        return f"The trade of game {number} ({st.game.template}) has not started. Use `/trade start`."
    lines = [_header(st), _prompt(st, factions)]
    if st.settings.starting_gold and not st.complete:
        lines.append(_gold_text(st))
    return "\n".join(lines)
