from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import commands.common as common
from commands.selection import _take_step
from locks import ThreadLocks
from rules.formats import parse_format
from state import make_event

A, B = 10, 20


@pytest.fixture
def setup(monkeypatch, el_classico, templates, factions):
    formats = {"el-classico": parse_format(el_classico, templates, factions)}
    events = [
        make_event(1, "match_started", format="el-classico", phase="Main", p1=A, p2=B),
        make_event(2, "coinflip", a=A, b=B),
    ]
    posted = []

    class FakeLog:
        def __init__(self, thread, bot_id):
            self.last_n = len(events)

        async def read(self):
            return events

        async def post(self, type, text, *, ping=None, **data):
            posted.append({"type": type, "text": text, "ping": ping, **data})

    monkeypatch.setattr(common, "ThreadLog", FakeLog)

    def interaction(user_id):
        thread = MagicMock(spec=discord.Thread)
        thread.id = 500
        return SimpleNamespace(
            client=SimpleNamespace(
                locks=ThreadLocks(),
                registry=SimpleNamespace(formats=formats, templates=templates),
                user=SimpleNamespace(id=7),
            ),
            channel=thread,
            user=SimpleNamespace(id=user_id),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
            delete_original_response=AsyncMock(),
        )

    return interaction, posted


async def test_ban_is_posted_and_pings_the_next_player(setup):
    interaction, posted = setup
    await _take_step(interaction(A), "ban", "jc")
    assert len(posted) == 1
    assert posted[0]["type"] == "ban" and posted[0]["template"] == "JC" and posted[0]["by"] == A
    assert posted[0]["ping"] == f"<@{B}>"
    assert "banned **JC**" in posted[0]["text"]


async def test_wrong_player_gets_a_private_refusal_and_nothing_is_posted(setup):
    interaction, posted = setup
    it = interaction(B)
    await _take_step(it, "ban", "JC")
    assert posted == []
    assert "not your turn" in it.followup.send.await_args.args[0]
    assert it.followup.send.await_args.kwargs["ephemeral"] is True
