"""Runs the real command handlers against a fake thread that remembers the events posted."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import commands.common as common
from commands import selection, trade as trade_commands
from locks import ThreadLocks
from rules.formats import parse_format
from state import make_event

A, B = 10, 20


class FakeThread:
    """Stands in for the Discord thread: keeps the events and the visible messages."""

    def __init__(self, first_events):
        self.events = list(first_events)
        self.messages = []
        self.said = []

    def log_class(self):
        thread = self

        class FakeLog:
            def __init__(self, _thread, _bot_id):
                self.last_n = len(thread.events)

            async def read(self):
                self.last_n = len(thread.events)
                return list(thread.events)

            async def post(self, type, text, *, ping=None, **data):
                event = make_event(len(thread.events) + 1, type, **data)
                thread.events.append(event)
                thread.messages.append({"type": type, "text": text, "ping": ping})
                self.last_n = event.n
                return event

            async def say(self, text, *, ping=None):
                thread.said.append(text)

        return FakeLog


def start_events():
    return [
        make_event(1, "match_started", format="el-classico", phase="Main", p1=A, p2=B),
        make_event(2, "coinflip", a=A, b=B),
    ]


@pytest.fixture
def world(monkeypatch, el_classico, templates, factions):
    def build(bo3=False):
        phase = el_classico["phases"][0]
        if bo3:
            phase["best_of"] = 3
            phase["selection"] = {
                "type": "sequence",
                "steps": [{"who": "A", "do": "pick"}, {"who": "B", "do": "pick"}],
                "game_order": ["pick_1", "pick_2", "decider"],
            }
        formats = {"el-classico": parse_format(el_classico, templates, factions)}
        thread = FakeThread(start_events())
        monkeypatch.setattr(common, "ThreadLog", thread.log_class())

        def interaction(user_id):
            channel = MagicMock(spec=discord.Thread)
            channel.id = 500
            return SimpleNamespace(
                client=SimpleNamespace(
                    locks=ThreadLocks(),
                    registry=SimpleNamespace(formats=formats, templates=templates, factions=factions),
                    user=SimpleNamespace(id=7),
                ),
                channel=channel,
                user=SimpleNamespace(id=user_id),
                response=SimpleNamespace(defer=AsyncMock()),
                followup=SimpleNamespace(send=AsyncMock()),
                delete_original_response=AsyncMock(),
            )

        return thread, interaction

    return build


def pair_of(thread, game=1):
    drawn = [e for e in thread.events if e.type == "pair_drawn" and e.data["game"] == game]
    return drawn[0].data["pair"]


async def test_last_ban_starts_the_trade_and_reports_finish_it(world):
    thread, interaction = world()
    await selection.ban.callback(interaction(A), "JC")
    assert thread.messages[-1]["type"] == "ban" and "pair_drawn" not in [m["type"] for m in thread.messages]
    await selection.ban.callback(interaction(B), "h3dm1")

    types = [m["type"] for m in thread.messages]
    assert types == ["ban", "ban", "pair_drawn"]
    assert "Game 1: 6lm10a" in thread.messages[-1]["text"]

    pair = pair_of(thread)
    await trade_commands.report.callback(interaction(A), pair[0], SimpleNamespace(id=A), 1000, None)
    await trade_commands.report.callback(interaction(B), "red", SimpleNamespace(id=B), 500, None)

    final = thread.messages[-1]["text"]
    assert "Lobby settings, game 1" in final
    assert [m["type"] for m in thread.messages[3:]] == ["faction_bid", "color_bid"]  # no next game in a BO1


async def test_wrong_player_cannot_ban_and_nothing_is_posted(world):
    thread, interaction = world()
    it = interaction(B)
    await selection.ban.callback(it, "JC")
    assert thread.messages == []
    assert "not your turn" in it.followup.send.await_args.args[0]


async def test_finishing_one_trade_starts_the_next_game(world):
    thread, interaction = world(bo3=True)
    await selection.pick.callback(interaction(A), "JC")
    await selection.pick.callback(interaction(B), "h3dm1")
    assert [m["type"] for m in thread.messages] == ["pick", "pick", "pair_drawn"]

    pair = pair_of(thread)
    await trade_commands.report.callback(interaction(A), pair[0], SimpleNamespace(id=A), 0, None)
    await trade_commands.report.callback(interaction(A), "red", SimpleNamespace(id=A), 0, None)

    posted = [(m["type"]) for m in thread.messages]
    assert posted[-2:] == ["color_bid", "pair_drawn"]  # game 1 done, game 2 started
    assert thread.events[-1].data["game"] == 2
    assert "Game 2: h3dm1" in thread.messages[-1]["text"]


async def test_trade_can_be_paused_and_game_two_continued_later(world):
    thread, interaction = world(bo3=True)
    await selection.pick.callback(interaction(A), "JC")
    await selection.pick.callback(interaction(B), "h3dm1")
    pair = pair_of(thread)
    await trade_commands.report.callback(interaction(A), pair[0], SimpleNamespace(id=A), 0, None)
    await trade_commands.report.callback(interaction(A), "red", SimpleNamespace(id=A), 0, None)
    before = len(thread.events)

    # "the next day": a fresh interaction with no memory except the thread
    later = interaction(B)
    await trade_commands.status.callback(later)
    assert len(thread.events) == before
    assert "Game 2: h3dm1" in thread.said[-1]


async def test_roll_command_splits_the_bans_text(world):
    thread, interaction = world()
    await selection.ban.callback(interaction(A), "JC")
    await selection.ban.callback(interaction(B), "h3dm1")
    pair = pair_of(thread)
    await trade_commands.roll.callback(interaction(A), f"{pair[0]}, ", None)
    roll_event = thread.events[-1]
    assert roll_event.type == "roll" and roll_event.data["bans"] == [pair[0]]
    assert pair[0] not in roll_event.data["pair"]


async def test_undo_removes_a_report_but_not_a_roll(world):
    thread, interaction = world()
    await selection.ban.callback(interaction(A), "JC")
    await selection.ban.callback(interaction(B), "h3dm1")
    pair = pair_of(thread)
    await trade_commands.roll.callback(interaction(A), None, None)
    it = interaction(B)
    await trade_commands.undo.callback(it)
    assert "Random results are final" in it.followup.send.await_args.args[0]

    await trade_commands.decline.callback(interaction(B), None)
    await trade_commands.undo.callback(interaction(B))
    assert thread.events[-1].type == "undo"
