"""The records a match is made of, and how they are written into and read back from messages.

The bot keeps no database. Every step of a match is one message in the match thread, and the
bot recognises its own steps by a tag at the start of the message:

    [#1 ms] Match started: <@111> vs <@222>. This is your match thread.

`#1` is the record number: 1, 2, 3, ... in the order posted, so a deleted message shows up as
a gap. `ms` is the code of the record type (here "match started"). The rest of the message is
ordinary text for the players. The data of the record is read out of that text, in a fixed
order from the start, by rules that depend on the code: for `ms`, the first two mentions are
the two players and the first `code quoted` words are the mode, the phase and, if the players
agreed on one, the template. Whatever comes after the data is free wording, and anything after the slots
that a code needs is never read.

A record that belongs to one game of the match (its trade) also names the game in the tag,
`[#7 tr g1]`. The numbering stays one sequence for the whole thread, so a deleted message is found
wherever it was, and the game marker is how the records of one game are picked out.

Either player can ask to undo the match from a record number, and the other must agree. The request and the
confirmation are records too (`ur` and `ud`). A confirmation says "everything from record N on no longer counts":
`effective_records` drops those records before anything else is worked out, so the selection, the trades and the
gold need no undo logic of their own. Nothing is deleted from the thread. The start and the coinflip can never be
undone, so they always count.

To know where a match stands, the bot reads the thread back and parses its own messages.
This module is plain Python (no Discord objects), so it can be tested.
"""

import re
from dataclasses import dataclass, field

from rules.ledger import spaced


class RecordError(ValueError):
    """A record is damaged or does not match its type."""


class MatchError(ValueError):
    """What a player asked is not possible in this match. The message is shown to the player."""


@dataclass(frozen=True)
class Record:
    n: int
    type: str
    data: dict = field(default_factory=dict)
    game: int | None = None  # the game this record belongs to, if it belongs to one


# Record type -> the data fields it carries. Each milestone adds the types it needs.
RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    # p1 started the match, p2 is the opponent (Discord user ids); the mode (format id), the phase (name)
    # and the template id the players agreed on (None when bans and picks choose the templates)
    "match_started": ("p1", "p2", "mode", "phase", "template"),
    "coinflip": ("winner",),  # the Discord user id of the coinflip winner, A
    "ban": ("player", "template"),  # who banned which template (Discord user id, template id)
    "pick": ("player", "template"),
    # the trade of one game (these records carry the game in the tag, see `TRADE_TYPES`)
    "trade_started": ("towns",),  # the town ids the bot drew: two, or one for a mirror
    "trade_resumed": (),  # a trade that was closed is opened again, where it stopped
    "town_bid": ("reporter", "winner", "amount", "town"),  # who reported, who won the bid, for how much, and the town chosen
    "color_bid": ("reporter", "winner", "amount", "color"),  # the same for the color ("red" or "blue")
    "first_choice_bid": ("reporter", "winner", "amount", "first"),  # the same for who chooses first, "hero" or "color"
    "pack_bid": ("reporter", "winner", "amount", "pack"),  # the same for the pack of computer-player towns ("pack1" or "pack2")
    "roll": ("player", "bans", "towns"),  # who rolled, the town ids they banned, and the new town(s) the bot drew
    "roll_skipped": ("player",),  # a player passes on the towns that stand (until the next roll)
    "hero_bans": ("player", "heroes"),  # a player bans these heroes (by name; none if they ban nobody) before the draw
    "heroes_drawn": ("heroes",),  # the heroes the bot drew (by name), in the order of the towns of the game
    "undo_requested": ("player", "start"),  # who asks to undo the match from record number `start`
    "undone": ("player", "start"),  # the other player agreed: record `start` and all after it no longer count
}

# Fields a record may also carry, because only some kinds of trade draw them. They are left out when there are none.
RECORD_OPTIONAL: dict[str, tuple[str, ...]] = {
    "trade_started": ("packs", "heroes"),  # the six towns of the two packs, pack1 first; the two heroes (by name)
    "roll": ("packs", "heroes"),  # the same, drawn again by the roll
}

TRADE_TYPES = (
    "trade_started", "trade_resumed", "town_bid", "pack_bid", "first_choice_bid", "color_bid", "roll", "roll_skipped",
    "hero_bans", "heroes_drawn",
)

# Record type -> the short code written in the tag.
CODES: dict[str, str] = {
    "match_started": "ms",
    "coinflip": "cf",
    "ban": "bn",
    "pick": "pk",
    "trade_started": "tr",
    "trade_resumed": "tu",
    "town_bid": "tb",
    "pack_bid": "pb",
    "first_choice_bid": "fb",
    "color_bid": "cb",
    "roll": "rl",
    "roll_skipped": "rs",
    "hero_bans": "hb",
    "heroes_drawn": "hd",
    "undo_requested": "ur",
    "undone": "ud",
}
_TYPE_OF_CODE = {code: type_ for type_, code in CODES.items()}

TAG = re.compile(r"^\[#(\d+) ([a-z]+)(?: g(\d+))?\]")
MENTION = re.compile(r"<@!?(\d+)>")  # how Discord writes a mention of a user in message text
QUOTED = re.compile(r"`([^`]+)`")  # a word the message writes as `code`, so it can be told apart from the wording


def _read_match_started(body: str) -> dict:
    ids = [int(found) for found in MENTION.findall(body)]
    if len(ids) < 2:
        raise RecordError("a match started message must mention both players")
    quoted = QUOTED.findall(body)
    if len(quoted) < 2:
        raise RecordError("a match started message must name the mode and the phase in `quotes`")
    template = quoted[2] if len(quoted) > 2 else None
    return {"p1": ids[0], "p2": ids[1], "mode": quoted[0], "phase": quoted[1], "template": template}


def _read_coinflip(body: str) -> dict:
    found = MENTION.search(body)
    if found is None:
        raise RecordError("a coinflip message must mention the winner")
    return {"winner": int(found.group(1))}


def _read_step(body: str) -> dict:
    """A ban or a pick: the player is the first mention, the template id the first `quoted` word."""
    player = MENTION.search(body)
    template = QUOTED.search(body)
    if player is None or template is None:
        raise RecordError("a ban or pick message must mention the player and give the template in `quotes`")
    return {"player": int(player.group(1)), "template": template.group(1)}


# Where the town(s) of a draw begin in the text of the bot's message, and where the packs of computer-player towns do.
# Without the marker, the words are read as they always were (the two towns of a standard pair).
_START_MARKER = re.compile(r"(?:Pair|Town):")
_ROLL_MARKER = re.compile(r"New (?:pair|town):")
_HEROES_MARKER = re.compile(r"Hero1:")  # where the heroes drawn with the towns begin: the line of the first hero
_PACKS_MARKER = re.compile(r"Packs:|Pack1:")  # where the packs begin: the line of pack1 (or an older "Packs:" line)


def _read_draw(text: str, error: str) -> dict:
    """The town(s) and the packs written after a marker: `towns` has one or two towns, `packs` six (or is left out)."""
    hero_found = _HEROES_MARKER.search(text)
    heroes = QUOTED.findall(text[hero_found.start() :]) if hero_found else []
    text = text[: hero_found.start()] if hero_found else text
    found = _PACKS_MARKER.search(text)
    towns_text, packs_text = (text[: found.start()], text[found.start() :]) if found else (text, "")
    towns, packs = QUOTED.findall(towns_text), QUOTED.findall(packs_text)
    if not 1 <= len(towns) <= 2:
        raise RecordError(error)
    if packs and len(packs) != 6:
        raise RecordError("the two packs of computer-player towns must give six towns in `quotes`")
    if heroes and len(heroes) != 2:
        raise RecordError("the heroes drawn with the towns must give two heroes in `quotes`")
    return {
        "towns": tuple(towns),
        **({"packs": tuple(packs)} if packs else {}),
        **({"heroes": tuple(heroes)} if heroes else {}),
    }


def _read_trade_started(body: str) -> dict:
    error = "a trade started message must give the two towns (or the one town of a mirror) in `quotes`"
    found = _START_MARKER.search(body)
    if found is not None:
        return _read_draw(body[found.end():], error)
    quoted = QUOTED.findall(body)
    if len(quoted) < 2:
        raise RecordError("a trade started message must give the two towns in `quotes`")
    return {"towns": (quoted[0], quoted[1])}


def _read_trade_resumed(body: str) -> dict:
    return {}


def _read_bid(choice_field: str):
    """A bid result: reporter and winner are the first two mentions, the amount and the choice the first two `quoted` words."""

    def read(body: str) -> dict:
        ids = [int(found) for found in MENTION.findall(body)]
        quoted = QUOTED.findall(body)
        if len(ids) < 2 or len(quoted) < 2:
            raise RecordError("a bid message must mention the reporter and the winner and give the amount and choice in `quotes`")
        amount = quoted[0].replace(" ", "")  # the bot writes 1 000 with a space
        if not amount.isdigit():
            raise RecordError(f"the amount of a bid must be a whole number, not {quoted[0]!r}")
        return {"reporter": ids[0], "winner": ids[1], "amount": int(amount), choice_field: quoted[1]}

    return read


def _read_roll(body: str) -> dict:
    """A roll: the roller is the first mention; the `quoted` words before "New pair:" (or "New town:") are the bans, the
    ones after it the new draw. Without that marker, the last two words are the new pair, any before them the bans."""
    player = MENTION.search(body)
    quoted = QUOTED.findall(body)
    if player is None:
        raise RecordError("a roll message must mention the player and give the new pair in `quotes`")
    found = _ROLL_MARKER.search(body)
    if found is not None:
        draw = _read_draw(body[found.end():], "a roll message must mention the player and give the new pair in `quotes`")
        return {"player": int(player.group(1)), "bans": tuple(QUOTED.findall(body[:found.start()])), **draw}
    if len(quoted) < 2:
        raise RecordError("a roll message must mention the player and give the new pair in `quotes`")
    return {"player": int(player.group(1)), "bans": tuple(quoted[:-2]), "towns": (quoted[-2], quoted[-1])}


def _read_roll_skipped(body: str) -> dict:
    player = MENTION.search(body)
    if player is None:
        raise RecordError("a skipped roll message must mention the player")
    return {"player": int(player.group(1))}


def _read_hero_bans(body: str) -> dict:
    """A player's hero bans: the player is the first mention, the banned heroes the `quoted` words (none: no ban)."""
    player = MENTION.search(body)
    if player is None:
        raise RecordError("a hero bans message must mention the player")
    return {"player": int(player.group(1)), "heroes": tuple(QUOTED.findall(body))}


def _read_heroes_drawn(body: str) -> dict:
    """The drawn heroes: every `quoted` word, in order."""
    heroes = QUOTED.findall(body)
    if not heroes:
        raise RecordError("a heroes drawn message must give the heroes in `quotes`")
    return {"heroes": tuple(heroes)}


def _read_undo(body: str) -> dict:
    """An undo request or confirmation: the player is the first mention, the record number the first `quoted` word."""
    player = MENTION.search(body)
    quoted = QUOTED.findall(body)
    if player is None or not quoted or not quoted[0].isdigit():
        raise RecordError("an undo message must mention the player and give the record number in `quotes`")
    return {"player": int(player.group(1)), "start": int(quoted[0])}


# Record type -> how to read its data out of the text after the tag.
READERS = {
    "match_started": _read_match_started,
    "coinflip": _read_coinflip,
    "ban": _read_step,
    "pick": _read_step,
    "trade_started": _read_trade_started,
    "trade_resumed": _read_trade_resumed,
    "town_bid": _read_bid("town"),
    "color_bid": _read_bid("color"),
    "pack_bid": _read_bid("pack"),
    "first_choice_bid": _read_bid("first"),
    "roll": _read_roll,
    "roll_skipped": _read_roll_skipped,
    "hero_bans": _read_hero_bans,
    "heroes_drawn": _read_heroes_drawn,
    "undo_requested": _read_undo,
    "undone": _read_undo,
}


def make_record(n: int, type: str, game: int | None = None, **data) -> Record:
    """Build a record, checking that it has exactly the fields its type needs. `game` is for records of one game."""
    if type not in RECORD_FIELDS:
        raise RecordError(f"unknown record type {type!r}")
    expected = set(RECORD_FIELDS[type])
    if not expected <= set(data) <= expected | set(RECORD_OPTIONAL.get(type, ())):
        raise RecordError(f"record {type!r} needs exactly {sorted(expected)}, got {sorted(data)}")
    return Record(n, type, data, game)


def tag(record: Record) -> str:
    """The tag that goes at the start of the record's message, for example `[#3 ms]` or `[#7 tr g1]`."""
    game = f" g{record.game}" if record.game is not None else ""
    return f"[#{record.n} {CODES[record.type]}{game}]"


def parse(text: str) -> Record | None:
    """Read a record from a message. None means the message is not a record; a damaged one raises."""
    found = TAG.match(text)
    if found is None:
        return None
    n, code = int(found.group(1)), found.group(2)
    type_ = _TYPE_OF_CODE.get(code)
    if type_ is None:
        raise RecordError(f"unknown record code {code!r}: {text[:80]!r}")
    game = int(found.group(3)) if found.group(3) else None
    return make_record(n, type_, game, **READERS[type_](text[found.end():]))


def _ai_words(packs: tuple[str, ...]) -> str:
    """The two packs of computer-player towns as ", AI: A, B, C vs D, E, F", or nothing when there are none."""
    half = len(packs) // 2
    return f", AI: {', '.join(packs[:half])} vs {', '.join(packs[half:])}" if packs else ""


def describe(record: Record) -> str:
    """One record in words. `<@id>` is how Discord writes a mention; it is only text here."""
    if record.type == "match_started":
        data = record.data
        template = f", template {data['template']}" if data["template"] else ""
        return f"match started: <@{data['p1']}> vs <@{data['p2']}>, mode {data['mode']}, phase {data['phase']}{template}"
    if record.type == "coinflip":
        return f"coinflip won by <@{record.data['winner']}>"
    if record.type in ("ban", "pick"):
        return f"<@{record.data['player']}> {record.type}s {record.data['template']}"
    if record.type == "trade_started":
        return f"game {record.game}: trade started, {' vs '.join(record.data['towns'])}{_ai_words(record.data.get('packs', ()))}"
    if record.type == "trade_resumed":
        return f"game {record.game}: trade reopened"
    if record.type == "roll":
        data = record.data
        bans = f", banning {', '.join(data['bans'])}" if data["bans"] else ""
        return f"game {record.game}: <@{data['player']}> rolled{bans}, new pair {' vs '.join(data['towns'])}{_ai_words(data.get('packs', ()))}"
    if record.type in ("undo_requested", "undone"):
        verb = "asks to undo" if record.type == "undo_requested" else "agreed to undo"
        return f"<@{record.data['player']}> {verb} everything from record {record.data['start']}"
    if record.type == "roll_skipped":
        return f"game {record.game}: <@{record.data['player']}> skipped the roll"
    if record.type == "hero_bans":
        banned = ", ".join(record.data["heroes"]) or "no hero"
        return f"game {record.game}: <@{record.data['player']}> banned {banned}"
    if record.type == "heroes_drawn":
        return f"game {record.game}: heroes drawn: {', '.join(record.data['heroes'])}"
    if record.type in ("town_bid", "pack_bid", "first_choice_bid", "color_bid"):
        data = record.data
        choice = data.get("town") or data.get("pack") or data.get("first") or data.get("color")
        return f"game {record.game}: <@{data['winner']}> won the {record.type.replace('_', ' ')} at {spaced(data['amount'])}, chose {choice}"
    return f"{record.type} {record.data}"


def describe_records(records: list[Record]) -> str:
    """What the bot found in a thread, as a numbered list."""
    if not records:
        return "I found no match records in this thread."
    try:
        counting = {r.n for r in effective_records(records)}
    except RecordError:
        counting = {r.n for r in records}  # a thread that cannot be trusted is reported elsewhere; just list it
    lines = [f"I read {len(records)} record(s) in this thread:"]
    for r in records:
        undone = " (undone)" if r.n not in counting and r.type not in UNDO_TYPES else ""
        lines.append(f"{r.n}. {describe(r)}{undone}")
    return "\n".join(lines)


@dataclass(frozen=True)
class Match:
    """Where a match stands, rebuilt from its records. It grows as the milestones add record types."""

    p1: int  # who started the match
    p2: int  # the opponent
    mode: str  # format id
    phase: str  # phase name
    template: str | None  # the template the players agreed on, if the phase has them agree
    a: int  # the coinflip winner
    b: int  # the other player
    taken: tuple[tuple[int, str, str], ...] = ()  # the bans and picks so far: (player id, "ban" or "pick", template id)
    trade_records: tuple[Record, ...] = ()  # the records of the trades, in order; `rules/trade.py` turns them into trades


def _only(records: list[Record], type: str, what: str) -> Record | None:
    found = [r for r in records if r.type == type]
    if len(found) > 1:
        raise RecordError(f"this thread has {len(found)} {what} messages, but a match has one, so I cannot tell which is right")
    return found[0] if found else None


START_TYPES = ("match_started", "coinflip")  # the records of the start of a match: they can never be undone
UNDO_TYPES = ("undo_requested", "undone")  # the records about undoing, which are not steps themselves


def steps_that_count(records: list[Record]) -> list[Record]:
    """The steps of the match that still count, oldest first: the records after the start and the coinflip,
    without the ones about undoing. Whatever an undo cancelled is not here."""
    return [r for r in effective_records(records) if r.type not in START_TYPES]


def effective_records(records: list[Record]) -> list[Record]:
    """The records that still count after the undos. The records about undoing are left out too.

    An `undone` record must follow, with nothing between, the request of the other player for the same record
    number, and must name a step that counts (not the start or the coinflip). Then that record and all after it
    stop counting. Anything else is reported rather than guessed.
    """
    active: list[Record] = []
    for position, record in enumerate(records):
        if record.type == "undo_requested":
            continue
        if record.type == "undone":
            asked = records[position - 1] if position > 0 else None
            if (
                asked is None
                or asked.type != "undo_requested"
                or asked.data["start"] != record.data["start"]
                or asked.data["player"] == record.data["player"]
            ):
                raise RecordError(
                    f"message #{record.n} undoes steps that the other player did not just ask to undo, "
                    "so I cannot tell how the match went"
                )
            start = record.data["start"]
            if start not in [r.n for r in active if r.type not in START_TYPES]:
                raise RecordError(
                    f"message #{record.n} undoes from record {start}, which is not a step that counts, "
                    "so I cannot tell how the match went"
                )
            active = [r for r in active if r.n < start]
            continue
        active.append(record)
    return active


def pending_undo(records: list[Record]) -> Record | None:
    """The undo request waiting for the other player: the last record, if it is a request."""
    return records[-1] if records and records[-1].type == "undo_requested" else None


def rebuild(records: list[Record]) -> Match:
    """The state of the match, from its records alone. Refuses to guess: whatever is wrong is said in words."""
    if not records:
        raise MatchError("This thread is not a match thread I know of.")

    for position, record in enumerate(records, start=1):
        if record.n > position:
            raise RecordError(
                f"message #{position} of this match is missing (someone deleted it), so I cannot tell how the match went"
            )
        if record.n < position:
            raise RecordError(f"message #{record.n} appears twice in this thread, so I cannot tell which one is right")

    records = effective_records(records)  # what is left after the undos
    start = _only(records, "match_started", "match start")
    if start is None:
        raise MatchError("This thread is not a match thread I know of.")
    flip = _only(records, "coinflip", "coinflip")
    if flip is None:
        raise RecordError("the coinflip of this match was not recorded (its message is missing), so I do not know who is A")
    winner = flip.data["winner"]
    p1, p2 = start.data["p1"], start.data["p2"]
    if winner not in (p1, p2):
        raise RecordError("the coinflip was won by somebody who is not a player of this match")
    steps = [r for r in records if r.type in ("ban", "pick")]
    if any(r.n < flip.n for r in steps):
        raise RecordError("a ban or pick comes before the coinflip in this thread, so I cannot tell how the match went")
    taken = tuple((r.data["player"], r.type, r.data["template"]) for r in steps)
    trades = tuple(r for r in records if r.type in TRADE_TYPES)
    for r in trades:
        if r.game is None:
            raise RecordError(f"message #{r.n} is part of a trade but does not say which game, so I cannot tell how the match went")
        if r.n < flip.n:
            raise RecordError("a trade comes before the coinflip in this thread, so I cannot tell how the match went")
    loser = p2 if winner == p1 else p1
    return Match(p1, p2, start.data["mode"], start.data["phase"], start.data["template"], winner, loser, taken, trades)


def describe_match(match: Match) -> str:
    """The state of the match in words. `<@id>` is how Discord writes a mention."""
    template = f", template {match.template}" if match.template else ""
    return "\n".join(
        [
            f"Match: <@{match.p1}> vs <@{match.p2}>",
            f"Mode {match.mode}, phase {match.phase}{template}",
            f"Coinflip: <@{match.a}> is A (acts first), <@{match.b}> is B",
        ]
    )


def players_of(records: list[Record]) -> tuple[int, int]:
    """The two players of the match: (who started it, the opponent)."""
    for record in records:
        if record.type == "match_started":
            return record.data["p1"], record.data["p2"]
    raise MatchError("This thread is not a match thread I know of.")


def check_player(records: list[Record], user_id: int) -> None:
    """Only the two players of a match may use its commands."""
    if user_id not in players_of(records):
        raise MatchError("Only the two players of this match can use this command.")
