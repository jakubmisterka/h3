"""The records a match is made of, and how they are written into and read back from messages.

The bot keeps no database. Every step of a match is one message in the match thread, and the
bot recognises its own steps by a tag at the start of the message:

    [#1 ms] Match started: <@111> vs <@222>. This is your match thread.

`#1` is the record number: 1, 2, 3, ... in the order posted, so a deleted message shows up as
a gap. `ms` is the code of the record type (here "match started"). The rest of the message is
ordinary text for the players. The data of the record is read out of that text, in a fixed
order from the start, by rules that depend on the code: for `ms`, the first two mentions are
the two players. Whatever comes after the data is free wording, and anything after the slots
that a code needs is never read.

To know where a match stands, the bot reads the thread back and parses its own messages.
This module is plain Python (no Discord objects), so it can be tested.
"""

import re
from dataclasses import dataclass, field


class RecordError(ValueError):
    """A record is damaged or does not match its type."""


class MatchError(ValueError):
    """What a player asked is not possible in this match. The message is shown to the player."""


@dataclass(frozen=True)
class Record:
    n: int
    type: str
    data: dict = field(default_factory=dict)


# Record type -> the data fields it carries. Each milestone adds the types it needs.
RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "match_started": ("p1", "p2"),  # p1 started the match, p2 is the opponent (Discord user ids)
}

# Record type -> the short code written in the tag.
CODES: dict[str, str] = {
    "match_started": "ms",
}
_TYPE_OF_CODE = {code: type_ for type_, code in CODES.items()}

TAG = re.compile(r"^\[#(\d+) ([a-z]+)\]")
MENTION = re.compile(r"<@!?(\d+)>")  # how Discord writes a mention of a user in message text


def _read_match_started(body: str) -> dict:
    ids = [int(found) for found in MENTION.findall(body)]
    if len(ids) < 2:
        raise RecordError("a match started message must mention both players")
    return {"p1": ids[0], "p2": ids[1]}


# Record type -> how to read its data out of the text after the tag.
READERS = {
    "match_started": _read_match_started,
}


def make_record(n: int, type: str, **data) -> Record:
    """Build a record, checking that it has exactly the fields its type needs."""
    if type not in RECORD_FIELDS:
        raise RecordError(f"unknown record type {type!r}")
    expected = set(RECORD_FIELDS[type])
    if set(data) != expected:
        raise RecordError(f"record {type!r} needs exactly {sorted(expected)}, got {sorted(data)}")
    return Record(n, type, data)


def tag(record: Record) -> str:
    """The tag that goes at the start of the record's message, for example `[#3 ms]`."""
    return f"[#{record.n} {CODES[record.type]}]"


def parse(text: str) -> Record | None:
    """Read a record from a message. None means the message is not a record; a damaged one raises."""
    found = TAG.match(text)
    if found is None:
        return None
    n, code = int(found.group(1)), found.group(2)
    type_ = _TYPE_OF_CODE.get(code)
    if type_ is None:
        raise RecordError(f"unknown record code {code!r}: {text[:80]!r}")
    return make_record(n, type_, **READERS[type_](text[found.end():]))


def describe(record: Record) -> str:
    """One record in words. `<@id>` is how Discord writes a mention; it is only text here."""
    if record.type == "match_started":
        return f"match started: <@{record.data['p1']}> vs <@{record.data['p2']}>"
    return f"{record.type} {record.data}"


def describe_records(records: list[Record]) -> str:
    """What the bot found in a thread, as a numbered list."""
    if not records:
        return "I found no match records in this thread."
    lines = [f"I read {len(records)} record(s) in this thread:"]
    lines += [f"{r.n}. {describe(r)}" for r in records]
    return "\n".join(lines)


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
