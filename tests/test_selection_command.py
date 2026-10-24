"""Tests /ban and /pick with a fake thread that keeps its messages, so a whole selection can be played."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import discord_commands.match as match
import discord_commands.selection as selection
from rules.formats import parse_format
from rules.registry import Registry

BOT = 7


class Person(SimpleNamespace):
    def __init__(self, user_id, name):
        super().__init__(id=user_id, mention=f"<@{user_id}>", display_name=name, bot=False)


ANNA, BORIS, OUTSIDER = Person(1, "Anna"), Person(2, "Boris"), Person(3, "Chris")


def make_thread(thread_id):
    """A stand-in thread: what the bot sends is kept, and read back by `history` like Discord would."""
    thread = MagicMock(spec=discord.Thread)
    thread.id = thread_id
    thread.messages = []

    async def send(content):
        await asyncio.sleep(0)  # a real send waits on Discord; other commands may run meanwhile
        thread.messages.append(SimpleNamespace(author=SimpleNamespace(id=BOT), content=content))

    def history(limit=None, oldest_first=False):
        async def messages():
            await asyncio.sleep(0)
            for message in list(thread.messages):
                yield message

        return messages()

    thread.send = send
    thread.history = history
    return thread


def texts(thread):
    return [message.content for message in thread.messages]


def interaction(registry, thread, user, in_thread=True):
    everything = SimpleNamespace(
        view_channel=True, send_messages=True, create_public_threads=True, create_private_threads=True,
        send_messages_in_threads=True, read_message_history=True,
    )
    return SimpleNamespace(
        user=user,
        channel=thread if in_thread else object(),
        app_permissions=everything,
        client=SimpleNamespace(registry=registry, user=SimpleNamespace(id=BOT)),
        response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


def told(it):
    """What the player was told privately."""
    if it.response.send_message.await_count:
        return it.response.send_message.await_args.args[0]
    return it.followup.send.await_args.args[0]


@pytest.fixture
def registry(good_format, templates, towns):
    ranked = dict(
        good_format,
        id="ranked",
        name="Ranked",
        templates=["JC", "6lm10a"],
        phases=[{"name": "Open", "best_of": 1, "template_selection": {"type": "agreed"}}],
    )
    formats = {data["id"]: parse_format(data, templates, towns) for data in (good_format, ranked)}
    return Registry(towns, templates, formats)


@pytest.fixture
def started(registry, monkeypatch):
    """A Sample Cup match (ban, ban, decider) that Anna won the coinflip of, as a thread."""
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)
    thread = make_thread(500)
    asyncio.run(match.begin_match(thread, BOT, registry, registry.formats["sample-cup"],
                                  registry.formats["sample-cup"].phases[0], None, ANNA, BORIS))
    return thread


def command(command_, registry, thread, user, template):
    it = interaction(registry, thread, user)
    asyncio.run(command_.callback(it, template))
    return it


# --- a whole selection -------------------------------------------------------------------------------------


def test_a_full_selection_ends_with_the_games(registry, started):
    first = command(selection.ban, registry, started, ANNA, "Jebus Cross")
    assert told(first) == "You banned Jebus Cross."
    command(selection.ban, registry, started, BORIS, "6lm10a")

    assert texts(started)[-1] == "The bans and picks are done. The games:\nGame 1: h3dm1"
    assert "[#3 bn] <@1> banned **Jebus Cross** (`JC`)" in texts(started)
    assert "[#4 bn] <@2> banned **6lm10a** (`6lm10a`)" in texts(started)


def test_each_step_shows_the_pool_and_names_who_is_next(registry, started):
    command(selection.ban, registry, started, ANNA, "JC")
    assert texts(started)[-2:] == [
        "Remaining (2): 6lm10a, h3dm1\nBanned: Jebus Cross. Picked: none.",
        "Step 2 of 2: <@2> bans a template with /ban",
    ]


def test_the_selection_continues_from_the_thread_alone(registry, started):
    command(selection.ban, registry, started, ANNA, "JC")
    # a restarted bot has the same thread and nothing else: a fresh registry object stands in for that
    again = Registry(registry.towns, registry.templates, dict(registry.formats))
    command(selection.ban, again, started, BORIS, "h3dm1")
    assert texts(started)[-1] == "The bans and picks are done. The games:\nGame 1: 6lm10a"


# --- refusals change nothing ---------------------------------------------------------------------------------


def test_the_wrong_player_is_refused_and_told_whose_step_it_is(registry, started):
    before = texts(started)
    it = command(selection.ban, registry, started, BORIS, "JC")
    assert "player A's step" in told(it)
    assert texts(started) == before


def test_the_wrong_action_is_refused(registry, started):
    before = texts(started)
    it = command(selection.pick, registry, started, ANNA, "JC")
    assert "A ban is expected now, not a pick" in told(it)
    assert texts(started) == before


def test_a_template_that_is_gone_is_refused_with_the_remaining_ones(registry, started):
    command(selection.ban, registry, started, ANNA, "JC")
    before = texts(started)
    it = command(selection.ban, registry, started, BORIS, "JC")
    assert "Remaining templates: 6lm10a, h3dm1" in told(it)
    assert texts(started) == before


def test_an_outsider_is_refused(registry, started):
    before = texts(started)
    it = command(selection.ban, registry, started, OUTSIDER, "JC")
    assert "Only the two players" in told(it)
    assert texts(started) == before


def test_outside_a_match_thread_the_player_is_sent_there(registry):
    it = interaction(registry, None, ANNA, in_thread=False)
    asyncio.run(selection.ban.callback(it, "JC"))
    assert "inside a match thread" in told(it)


def test_nothing_more_is_accepted_after_the_last_step(registry, started):
    command(selection.ban, registry, started, ANNA, "JC")
    command(selection.ban, registry, started, BORIS, "6lm10a")
    it = command(selection.ban, registry, started, ANNA, "h3dm1")
    assert "finished" in told(it)


def test_a_match_with_an_agreed_template_has_no_bans(registry, monkeypatch):
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)
    thread = make_thread(501)
    fmt = registry.formats["ranked"]
    asyncio.run(match.begin_match(thread, BOT, registry, fmt, fmt.phases[0], "JC", ANNA, BORIS))
    it = command(selection.ban, registry, thread, ANNA, "JC")
    assert "no bans or picks" in told(it)


def test_a_thread_that_does_not_follow_the_rules_is_not_trusted(registry, started):
    # somebody removed the first ban from the record but the second one is still there
    command(selection.ban, registry, started, ANNA, "JC")
    command(selection.ban, registry, started, BORIS, "6lm10a")
    del started.messages[6:8]  # Anna's ban and the messages that followed it
    it = command(selection.ban, registry, started, ANNA, "h3dm1")
    assert "missing" in told(it) or "does not follow" in told(it)


# --- two commands at once ------------------------------------------------------------------------------------


def test_the_same_player_sending_two_bans_at_once_only_gets_the_first_through(registry, started):
    async def both():
        first = interaction(registry, started, ANNA)
        second = interaction(registry, started, ANNA)
        await asyncio.gather(selection.ban.callback(first, "JC"), selection.ban.callback(second, "6lm10a"))
        return first, second

    first, second = asyncio.run(both())
    bans = [text for text in texts(started) if " bn]" in text]
    assert len(bans) == 1 and "[#3 bn]" in bans[0]
    assert "player B's step" in told(second)


# --- what is offered while typing ---------------------------------------------------------------------------------


def test_only_the_remaining_templates_are_offered(registry, started):
    command(selection.ban, registry, started, ANNA, "JC")
    choices = asyncio.run(selection.remaining_options(interaction(registry, started, BORIS), ""))
    assert [(c.name, c.value) for c in choices] == [("6lm10a", "6lm10a"), ("h3dm1", "h3dm1")]


def test_offered_templates_are_filtered_by_what_is_typed(registry, started):
    choices = asyncio.run(selection.remaining_options(interaction(registry, started, ANNA), "jeb"))
    assert [c.value for c in choices] == ["JC"]


def test_nothing_is_offered_outside_a_match_thread(registry):
    it = interaction(registry, None, ANNA, in_thread=False)
    assert asyncio.run(selection.remaining_options(it, "")) == []


def test_the_commands_are_called_ban_and_pick_and_take_a_template():
    assert (selection.ban.name, selection.pick.name) == ("ban", "pick")
    assert {p.name: p.required for p in selection.ban.parameters} == {"template": True}
