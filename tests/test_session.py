from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import commands.common as common
from locks import ThreadLocks
from rules.errors import UserError
from rules.formats import parse_format
from state import make_event

P1, P2, OUTSIDER = 1, 2, 99


@pytest.fixture
def formats(el_classico, templates, factions):
    return {"el-classico": parse_format(el_classico, templates, factions)}


def make_interaction(formats, user_id=P1, channel="thread"):
    if channel == "thread":
        channel = MagicMock(spec=discord.Thread)
        channel.id = 500
    return SimpleNamespace(
        client=SimpleNamespace(locks=ThreadLocks(), registry=SimpleNamespace(formats=formats), user=SimpleNamespace(id=7)),
        channel=channel,
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        delete_original_response=AsyncMock(),
    )


def match_events():
    return [
        make_event(1, "match_started", format="el-classico", phase="Main", p1=P1, p2=P2),
        make_event(2, "coinflip", a=P1, b=P2),
    ]


@pytest.fixture
def thread_events(monkeypatch):
    """Make the session read these events instead of a real thread."""
    holder = {"events": match_events()}

    class FakeLog:
        def __init__(self, thread, bot_id):
            pass

        async def read(self):
            return holder["events"]

    monkeypatch.setattr(common, "ThreadLog", FakeLog)
    return holder


async def test_player_in_a_match_thread_gets_the_match(formats, thread_events):
    interaction = make_interaction(formats)
    async with common.match_session(interaction) as session:
        match, _ = session
        assert match.players == (P1, P2)
    interaction.delete_original_response.assert_awaited_once()


async def test_outsider_is_refused_and_nothing_runs(formats, thread_events):
    interaction = make_interaction(formats, user_id=OUTSIDER)
    ran = False
    async with common.match_session(interaction) as session:
        if session is not None:
            ran = True
    assert not ran
    message = interaction.followup.send.await_args.args[0]
    assert "Only the two players" in message
    assert interaction.followup.send.await_args.kwargs["ephemeral"] is True


async def test_command_outside_a_thread_says_to_use_the_match_thread(formats, thread_events):
    interaction = make_interaction(formats, channel=object())
    async with common.match_session(interaction) as session:
        assert session is None
    assert interaction.followup.send.await_args.args[0] == common.NOT_IN_THREAD


async def test_thread_without_a_match_is_explained(formats, thread_events):
    thread_events["events"] = []
    interaction = make_interaction(formats)
    async with common.match_session(interaction) as session:
        assert session is None
    assert "no match in this thread" in interaction.followup.send.await_args.args[0]


async def test_deleted_message_is_reported_not_guessed(formats, thread_events):
    events = match_events() + [make_event(4, "ban", by=P1, template="JC")]  # event 3 is missing
    thread_events["events"] = events
    interaction = make_interaction(formats)
    async with common.match_session(interaction) as session:
        assert session is None
    assert "message is missing" in interaction.followup.send.await_args.args[0]


async def test_user_error_inside_the_block_is_shown_to_the_player(formats, thread_events):
    interaction = make_interaction(formats)
    async with common.match_session(interaction):
        raise UserError("It is not your turn.")
    assert interaction.followup.send.await_args.args[0] == "It is not your turn."
    interaction.delete_original_response.assert_not_awaited()


async def test_unexpected_errors_are_not_swallowed(formats, thread_events):
    interaction = make_interaction(formats)
    with pytest.raises(RuntimeError):
        async with common.match_session(interaction):
            raise RuntimeError("bug")


async def test_session_holds_the_thread_lock(formats, thread_events):
    interaction = make_interaction(formats)
    async with common.match_session(interaction):
        assert 500 in interaction.client.locks._entries
    assert interaction.client.locks._entries == {}
