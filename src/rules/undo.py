"""Undoing steps of a match: what a request would undo, whether it is a new request, a repeat or a confirmation, and
the words the bot posts.

Plain Python: no Discord objects in here, so tests can cover it. Undo is a rewind: asking to undo from record N means
that record and every later step stop counting, whatever kind of step they are. The match itself never changes in
place: `state.effective_records` leaves the cancelled records out when the thread is read. Both players must agree,
so the first player's request waits, and the other player confirms by running `/match undo` right after.
"""

from dataclasses import dataclass

from rules.catalogue import Catalogue
from state import START_TYPES, UNDO_TYPES, Record, effective_records, pending_undo, steps_that_count


class UndoError(ValueError):
    """The undo cannot be asked for. The message is shown to the player."""


@dataclass(frozen=True)
class UndoPlan:
    start: int  # the first record that would stop counting
    removed: tuple[Record, ...]  # that record and every step after it that counts, oldest first


###### Wording: what the bot says about an undo ################################################################
# The sentences the bot says. To change a wording, change it here; the logic that decides when is further down.

CHECK_STATUS = "Check /match status to see where the match stands."
UNDONE_REPLY = "Undone."


def step_words(record: Record, templates: Catalogue, towns: Catalogue) -> str:
    """One step in a few words."""
    data = record.data
    who = f"<@{data['player']}>" if "player" in data else ""
    if record.type in ("ban", "pick"):
        return f"{who} {'banned' if record.type == 'ban' else 'picked'} {templates.find(data['template']).name}"
    game = f"game {record.game}: "
    if record.type == "trade_started":
        first, second = (towns.find(town).name for town in data["pair"])
        return f"{game}the trade started ({first} vs {second})"
    if record.type == "trade_resumed":
        return f"{game}the trade was reopened"
    if record.type == "roll":
        bans = ", ".join(towns.find(town).name for town in data["bans"])
        first, second = (towns.find(town).name for town in data["pair"])
        return f"{game}{who} rolled{', banning ' + bans if bans else ''} (new pair {first} vs {second})"
    if record.type == "roll_skipped":
        return f"{game}{who} skipped the roll"
    if record.type in ("town_bid", "color_bid"):
        choice = towns.find(data["town"]).name if record.type == "town_bid" else data["color"]
        what = record.type.replace("_", " ")
        return f"{game}{what}, <@{data['winner']}> won at {data['amount']} and chose {choice}"
    return record.type  # a kind of step this function does not know yet: its name is better than nothing


def request_text(
    player: str, other: str, plan: UndoPlan, templates: Catalogue, towns: Catalogue, replaces: bool = False
) -> str:
    """The text of the request record. `player` and `other` are mentions. The first mention is the one who asks and
    the first `quoted` word the record number, which is how the record is read back. `replaces` says that a request
    was waiting and this one takes its place."""
    first = plan.removed[0]
    later = len(plan.removed) - 1
    everything = f" and the {later} step{'s' if later != 1 else ''} after it" if later else ""
    replacing = " This replaces the earlier request." if replaces else ""
    return (
        f"{player} asks to undo from record `{plan.start}` ({step_words(first, templates, towns)}){everything}. "
        f"{CHECK_STATUS}{replacing}\n{other}, to agree, run /match undo"
    )


def undone_text(player: str, start: int) -> str:
    """The text of the confirmation record. The first mention is the player who agreed, the first `quoted` word the number."""
    return f"{player} agreed: the match is back to how it was before record `{start}`."


def asked_reply(other: str) -> str:
    """The private reply to the player who asked. `other` is the mention of the player who has to agree."""
    return f"Asked. {other} has to agree."


def waiting_reply(other: str) -> str:
    """The private reply to the player who asked and asks again before the other has answered."""
    return f"You already asked. Waiting for {other} to run /match undo."


################################################################################################################


def plan_undo(records: list[Record], start: int | None) -> UndoPlan:
    """What undoing from record number `start` (default: the latest step) would cancel. Raises UndoError."""
    steps = steps_that_count(records)
    if not steps:
        raise UndoError("There is nothing to undo yet: only the start and the coinflip have happened.")
    if start is None:
        start = steps[-1].n
    counting = [r.n for r in effective_records(records)]
    if start in [r.n for r in records if r.type in START_TYPES]:
        raise UndoError("The start of the match and the coinflip cannot be undone.")
    if start not in [r.n for r in steps]:
        if start in [r.n for r in records if r.type not in UNDO_TYPES] and start not in counting:
            raise UndoError(f"Record {start} was already undone. {CHECK_STATUS}")
        raise UndoError(f"Record {start} is not a step of this match. {CHECK_STATUS}")
    return UndoPlan(start, tuple(r for r in steps if r.n >= start))


def next_undo(records: list[Record], user_id: int, start: int | None) -> tuple[str, UndoPlan]:
    """What running the undo command means right now.

    ("confirm", plan): the other player asked, nothing was posted since, and this player named the same record or
    no record at all. ("waiting", plan): this player is the one who asked. ("request", plan): anything else is a
    new request. Raises UndoError when there is nothing to undo or the record cannot be undone.
    """
    pending = pending_undo(records)
    if pending is not None and start in (None, pending.data["start"]):
        plan = plan_undo(records, pending.data["start"])
        return ("waiting" if pending.data["player"] == user_id else "confirm"), plan
    return "request", plan_undo(records, start)
