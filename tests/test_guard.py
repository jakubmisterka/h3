"""Tests the guard with fake Discord objects, so no connection to Discord is needed."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import discord_commands.guard as guard
from state import RecordError, make_record

ANNA, BORIS, OUTSIDER, BOT = 111, 222, 333, 7
ALLOWED = SimpleNamespace(view_channel=True, read_message_history=True)


def interaction(user_id=ANNA, in_thread=True, permissions=ALLOWED):
    channel = MagicMock(spec=discord.Thread) if in_thread else object()
    return SimpleNamespace(
        channel=channel,
        user=SimpleNamespace(id=user_id),
        client=SimpleNamespace(user=SimpleNamespace(id=BOT)),
        app_permissions=permissions,
        response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


@pytest.fixture
def thread_records(monkeypatch):
    """Make the guard read these records (or fail) instead of a real thread."""
    state = {"records": [
            make_record(1, "match_started", p1=ANNA, p2=BORIS, mode="sample-cup", phase="Main", template=None),
            make_record(2, "coinflip", winner=ANNA),
        ], "error": None, "reads": 0}

    class FakeLog:
        def __init__(self, thread, bot_id):
            pass

        async def read(self):
            state["reads"] += 1
            if state["error"]:
                raise state["error"]
            return state["records"]

    monkeypatch.setattr(guard, "ThreadLog", FakeLog)
    return state


def run(it):
    return asyncio.run(guard.guarded_records(it))


def told_user(it):
    """What the user was told, from whichever reply was used."""
    if it.response.send_message.await_count:
        return it.response.send_message.await_args.args[0]
    return it.followup.send.await_args.args[0]


def test_each_player_gets_the_records(thread_records):
    for player in (ANNA, BORIS):
        it = interaction(user_id=player)
        assert run(it) == thread_records["records"]
        it.followup.send.assert_not_awaited()


def test_on_success_the_reply_is_acknowledged_privately(thread_records):
    it = interaction()
    run(it)
    it.response.defer.assert_awaited_once_with(ephemeral=True)


def test_somebody_else_is_refused_and_told_why(thread_records):
    it = interaction(user_id=OUTSIDER)
    assert run(it) is None
    assert "Only the two players" in told_user(it)


def test_outside_a_thread_the_user_is_sent_to_the_match_thread(thread_records):
    it = interaction(in_thread=False)
    assert run(it) is None
    assert told_user(it) == guard.NOT_IN_THREAD
    assert it.response.send_message.await_args.kwargs["ephemeral"] is True
    assert thread_records["reads"] == 0  # nothing was read


def test_a_thread_without_a_match_is_explained(thread_records):
    thread_records["records"] = []
    it = interaction()
    assert run(it) is None
    assert "not a match thread" in told_user(it)


def test_missing_history_permission_is_named_before_anything_is_read(thread_records):
    it = interaction(permissions=SimpleNamespace(view_channel=True, read_message_history=False))
    assert run(it) is None
    assert "Read Message History" in told_user(it)
    assert thread_records["reads"] == 0


def test_a_damaged_record_is_reported_not_guessed(thread_records):
    thread_records["error"] = RecordError("damaged record")
    it = interaction()
    assert run(it) is None
    assert "I can't read this thread" in told_user(it)


def test_a_thread_with_a_deleted_message_is_refused_for_every_command(thread_records):
    del thread_records["records"][1]  # the coinflip
    it = interaction()
    assert run(it) is None
    assert "coinflip of this match was not recorded" in told_user(it)
    assert "can't read this thread" in told_user(it)
