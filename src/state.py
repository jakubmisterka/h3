"""Match state: the events a match is made of, and how to rebuild a match from them.

The bot keeps no data outside the Discord thread. Every accepted action is posted
as one message that carries an *event*; to serve a command the bot reads the
thread, decodes the events and folds them into a `Match`. This module is plain
Python (no Discord objects), so all of it can be unit-tested.

Every event has a number `n`: 1, 2, 3, ... in the order posted. If a message in
the middle of the thread was deleted, the numbers have a gap and the match is
reported as not rebuildable instead of being guessed.
"""

import json
from dataclasses import dataclass, field

from rules.formats import Format, Phase

PREFIX = "h3:"

# Event type -> the data fields it must carry.
EVENT_FIELDS: dict[str, tuple[str, ...]] = {
    "match_started": ("format", "phase", "p1", "p2"),  # optional: "template" (agreed phases)
    "coinflip": ("a", "b"),  # a = coinflip winner
    "ban": ("by", "template"),
    "pick": ("by", "template"),
    # Trade events. `game` is the 1-based game number.
    "pair_drawn": ("game", "pair"),  # the first pair, drawn by the bot when the trade starts
    "roll": ("game", "by", "bans", "pair"),  # `pair` is the new pair the bot drew for this roll
    "decline": ("game", "by"),
    "faction_bid": ("game", "by", "winner", "amount", "faction"),  # `by` reported it
    "color_bid": ("game", "by", "winner", "amount", "color"),
    "color_toss": ("game", "winner"),  # drawn by the bot
    "color_choice": ("game", "by", "color"),
    "undo": ("game", "by"),
}

# Player reports: the only trade events that undo may remove.
# Random draws (pair_drawn, color_toss) and the rolls that cause them are final.
UNDOABLE = frozenset({"decline", "faction_bid", "color_bid", "color_choice"})


class StateError(ValueError):
    """The thread does not hold a match the bot can rebuild."""


@dataclass(frozen=True)
class Event:
    n: int
    type: str
    data: dict = field(default_factory=dict)


def make_event(n: int, type: str, **data) -> Event:
    """Build an event, checking that it carries exactly what its type needs."""
    if type not in EVENT_FIELDS:
        raise StateError(f"unknown event type {type!r}")
    missing = [f for f in EVENT_FIELDS[type] if f not in data]
    if missing:
        raise StateError(f"event {type!r} is missing {', '.join(missing)}")
    return Event(n, type, data)


def encode(event: Event) -> str:
    """The machine part of a bot message, small enough for an embed footer."""
    return PREFIX + json.dumps({"n": event.n, "t": event.type, **event.data}, separators=(",", ":"))


def decode(text: str) -> Event | None:
    """Read an event from message text. None means 'not an event'; a broken event raises."""
    if not text.startswith(PREFIX):
        return None
    try:
        raw = json.loads(text[len(PREFIX):])
        n, type_ = raw.pop("n"), raw.pop("t")
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        raise StateError(f"a bot message holds a damaged event: {text[:60]!r}") from e
    if not isinstance(n, int):
        raise StateError(f"a bot message holds a damaged event number: {text[:60]!r}")
    return make_event(n, type_, **raw)


@dataclass
class Match:
    """Everything known about a match, built from its events."""

    format: Format
    phase: Phase
    players: tuple[int, int]  # (who started it, opponent)
    agreed_template: str | None = None
    a: int | None = None  # coinflip winner
    b: int | None = None
    selection: list[Event] = field(default_factory=list)  # bans and picks, in order
    trade: dict[int, list[Event]] = field(default_factory=dict)  # per game number
    last_n: int = 0

    def is_player(self, user_id: int) -> bool:
        return user_id in self.players

    def other(self, user_id: int) -> int:
        return self.players[1] if user_id == self.players[0] else self.players[0]

    def side_of(self, user_id: int) -> str:
        """'A' for the coinflip winner, 'B' for the other player."""
        return "A" if user_id == self.a else "B"

    def user_of(self, side: str) -> int:
        return self.a if side == "A" else self.b


def fold(events: list[Event], formats: dict[str, Format]) -> Match:
    """Rebuild a match from its events, oldest first. Raises StateError if it cannot."""
    if not events:
        raise StateError("there is no match in this thread")

    for expected, event in enumerate(events, start=1):
        if event.n != expected:
            raise StateError(
                f"a bot message is missing: event {expected} was expected but event {event.n} came next"
            )

    first = events[0]
    if first.type != "match_started":
        raise StateError("the message that started the match is missing")
    d = first.data
    fmt = formats.get(d["format"])
    if fmt is None:
        raise StateError(f"the format {d['format']!r} of this match no longer exists")
    phase = next((p for p in fmt.phases if p.name == d["phase"]), None)
    if phase is None:
        raise StateError(f"the format {fmt.name} has no phase {d['phase']!r} any more")

    match = Match(
        format=fmt,
        phase=phase,
        players=(d["p1"], d["p2"]),
        agreed_template=d.get("template"),
        last_n=first.n,
    )

    for event in events[1:]:
        match.last_n = event.n
        if event.type == "match_started":
            raise StateError("this thread holds two match starts")
        elif event.type == "coinflip":
            match.a, match.b = event.data["a"], event.data["b"]
        elif event.type in ("ban", "pick"):
            match.selection.append(event)
        elif event.type == "undo":
            game_events = match.trade.get(event.data["game"], [])
            if game_events and game_events[-1].type in UNDOABLE:
                game_events.pop()
        else:
            match.trade.setdefault(event.data["game"], []).append(event)
    return match
