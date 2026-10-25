"""Tests /match start with fake Discord objects, so no connection to Discord is needed."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import discord_commands.match as match
from rules.formats import parse_format
from rules.registry import Registry
from rules.start import coinflip_announcement, mode_choices, template_choices
from state import make_record, parse

BOT = 7


class FakeThread:
    def __init__(self):
        self.id = 1
        self.sent = []
        self.add_user = AsyncMock()
        self.mention = "<#thread>"

    async def send(self, content):
        self.sent.append(content)


def person(user_id, name, bot=False):
    return SimpleNamespace(id=user_id, mention=f"<@{user_id}>", display_name=name, bot=bot)


ANNA, BORIS = person(1, "Anna"), person(2, "Boris")


def registry_of(templates, towns, *formats):
    parsed = [parse_format(data, templates, towns) for data in formats]
    return Registry(towns, templates, {fmt.id: fmt for fmt in parsed})


@pytest.fixture
def sample(good_format):
    return good_format


@pytest.fixture
def ranked(good_format):
    """A made-up mode where the players agree on the template."""
    return dict(
        good_format,
        id="ranked",
        name="Ranked",
        templates=["JC", "6lm10a"],
        phases=[{"name": "Open", "best_of": 1, "template_selection": {"type": "agreed"}}],
    )


@pytest.fixture
def secret(good_format):
    return dict(good_format, id="secret-cup", name="Secret Cup", thread_visibility="private")


@pytest.fixture
def old(good_format):
    return dict(good_format, id="old-cup", name="Old Cup", status="archived")


def interaction(registry, thread, user=ANNA, in_text_channel=True):
    channel = MagicMock(spec=discord.TextChannel) if in_text_channel else object()
    if in_text_channel:
        channel.create_thread = AsyncMock(return_value=thread)
    announcement = SimpleNamespace(create_thread=AsyncMock(return_value=thread))
    everything = SimpleNamespace(
        view_channel=True,
        send_messages=True,
        create_public_threads=True,
        create_private_threads=True,
        send_messages_in_threads=True,
        read_message_history=True,
    )
    return SimpleNamespace(
        user=user,
        channel=channel,
        app_permissions=everything,
        client=SimpleNamespace(registry=registry, user=SimpleNamespace(id=BOT)),
        response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        original_response=AsyncMock(return_value=announcement),
        edit_original_response=AsyncMock(),
        announcement=announcement,
    )


def start(it, mode, opponent=BORIS, phase=None, template=None):
    asyncio.run(match.start.callback(it, mode, opponent, phase, template))


def records_in(thread):
    """The records among the messages of a thread; the rest is plain text for the players."""
    return [record for record in map(parse, thread.sent) if record is not None]


def coinflip_message(thread):
    """The text of the coinflip record."""
    return next(text for text in thread.sent if text.startswith("[#2 cf]"))


def refusal(it):
    return it.response.send_message.await_args.args[0]


@pytest.fixture
def anna_wins(monkeypatch):
    monkeypatch.setattr(match, "coinflip", lambda a, b: a)


# --- starting a match ------------------------------------------------------------------------------


def test_a_public_match_gets_a_thread_with_the_start_and_the_coinflip(sample, templates, towns, anna_wins):
    thread = FakeThread()
    it = interaction(registry_of(templates, towns, sample), thread)
    start(it, "sample-cup")

    it.announcement.create_thread.assert_awaited_once()
    records = records_in(thread)
    assert [r.type for r in records] == ["match_started", "coinflip"]
    assert records[0].data == {"p1": 1, "p2": 2, "mode": "sample-cup", "phase": "Main", "template": None}
    assert records[1].data == {"winner": 1}
    assert "<@1> wins and is A, so <@1> bans first" in coinflip_message(thread)


def test_the_coinflip_can_be_won_by_the_opponent(sample, templates, towns, monkeypatch):
    monkeypatch.setattr(match, "coinflip", lambda a, b: b)
    thread = FakeThread()
    start(interaction(registry_of(templates, towns, sample), thread), "sample-cup")
    assert parse(coinflip_message(thread)).data == {"winner": 2}
    assert "<@2> wins and is A" in coinflip_message(thread)


def test_the_mode_can_be_named_by_its_name(sample, templates, towns, anna_wins):
    thread = FakeThread()
    start(interaction(registry_of(templates, towns, sample), thread), "Sample Cup")
    assert parse(thread.sent[0]).data["mode"] == "sample-cup"


def test_a_private_format_gets_a_private_thread_and_a_private_reply(secret, templates, towns, anna_wins):
    thread = FakeThread()
    it = interaction(registry_of(templates, towns, secret), thread)
    start(it, "secret-cup")

    assert it.channel.create_thread.await_args.kwargs["type"] == discord.ChannelType.private_thread
    assert thread.add_user.await_count == 2
    assert it.response.defer.await_args.kwargs == {"ephemeral": True}
    it.announcement.create_thread.assert_not_awaited()
    assert [r.type for r in records_in(thread)] == ["match_started", "coinflip"]


def test_a_public_format_does_not_use_a_private_thread(sample, templates, towns, anna_wins):
    it = interaction(registry_of(templates, towns, sample), FakeThread())
    start(it, "sample-cup")
    it.channel.create_thread.assert_not_awaited()


def test_an_agreed_template_is_recorded(ranked, templates, towns, anna_wins):
    thread = FakeThread()
    start(interaction(registry_of(templates, towns, ranked), thread), "ranked", template="Jebus Cross")
    assert parse(thread.sent[0]).data["template"] == "JC"
    assert coinflip_message(thread).startswith("[#2 cf] Coinflip: <@1> wins and is A, <@2> is B.")


def test_the_rules_come_one_per_message_between_the_start_and_the_coinflip(sample, templates, towns, anna_wins):
    thread = FakeThread()
    start(interaction(registry_of(templates, towns, sample), thread), "sample-cup")
    assert [parse(text) is not None for text in thread.sent[:7]] == [True, False, False, False, False, False, True]
    assert thread.sent[1:6] == [
        "Best of 1",
        "Template Selection: AB",
        "A bans, B bans, then decider",
        "The winner of the coinflip will be player A, the other player is B",
        "Templates: Jebus Cross, 6lm10a, h3dm1",
    ]


def test_the_first_step_is_announced_after_the_coinflip(sample, templates, towns, anna_wins):
    thread = FakeThread()
    start(interaction(registry_of(templates, towns, sample), thread), "sample-cup")
    assert thread.sent[7:] == [
        "Remaining (3): Jebus Cross, 6lm10a, h3dm1",
        "Step 1 of 2: <@1> bans a template with /ban",
    ]


def test_an_agreed_phase_goes_straight_to_the_game(ranked, templates, towns, anna_wins):
    thread = FakeThread()
    start(interaction(registry_of(templates, towns, ranked), thread), "ranked", template="JC")
    assert len(thread.sent) == 7 and thread.sent[-3].startswith("[#2 cf]")
    assert thread.sent[-2:] == ["Game 1: Jebus Cross", "Start its trade with /trade start."]  # straight to the game


def test_an_agreed_template_is_stated_instead_of_a_selection(ranked, templates, towns, anna_wins):
    thread = FakeThread()
    start(interaction(registry_of(templates, towns, ranked), thread), "ranked", template="JC")
    assert thread.sent[1:4] == [
        "Best of 1",
        "The players agreed on the template: Jebus Cross",
        "The winner of the coinflip will be player A, the other player is B",
    ]


# --- refusals: no thread, a private explanation ------------------------------------------------------


def test_an_unknown_mode_is_refused_and_lists_the_modes(sample, templates, towns):
    it = interaction(registry_of(templates, towns, sample), FakeThread())
    start(it, "nope")
    assert "There is no mode called 'nope'. Available modes: Sample Cup." in refusal(it)
    assert it.response.send_message.await_args.kwargs == {"ephemeral": True}
    it.response.send_message.assert_awaited_once()
    it.announcement.create_thread.assert_not_awaited()


def test_an_archived_mode_is_refused(sample, old, templates, towns):
    it = interaction(registry_of(templates, towns, sample, old), FakeThread())
    start(it, "old-cup")
    assert "archived" in refusal(it)


def test_a_missing_template_is_refused_before_any_thread_exists(ranked, templates, towns):
    thread = FakeThread()
    it = interaction(registry_of(templates, towns, ranked), thread)
    start(it, "ranked")
    assert "agree on the template" in refusal(it)
    assert thread.sent == []
    it.announcement.create_thread.assert_not_awaited()


def test_a_wrong_phase_is_refused(sample, templates, towns):
    it = interaction(registry_of(templates, towns, sample), FakeThread())
    start(it, "sample-cup", phase="Final")
    assert "no phase called 'Final'" in refusal(it)


def test_yourself_and_bots_are_still_refused(sample, templates, towns):
    reg = registry_of(templates, towns, sample)
    it = interaction(reg, FakeThread())
    start(it, "sample-cup", opponent=ANNA)
    assert "yourself" in refusal(it)
    it = interaction(reg, FakeThread())
    start(it, "sample-cup", opponent=person(9, "Robot", bot=True))
    assert "bot" in refusal(it)


def test_a_missing_permission_is_named_before_anything_is_posted(secret, templates, towns):
    it = interaction(registry_of(templates, towns, secret), FakeThread())
    it.app_permissions.create_private_threads = False
    start(it, "secret-cup")
    assert "Create Private Threads" in refusal(it)
    it.channel.create_thread.assert_not_awaited()


def test_the_command_takes_a_mode_an_opponent_and_optional_phase_and_template():
    assert {p.name: p.required for p in match.start.parameters} == {
        "mode": True,
        "opponent": True,
        "phase": False,
        "template": False,
    }


# --- the announcement and the choices offered while typing ------------------------------------------


def test_the_announcement_says_what_the_first_step_is(sample, templates, towns):
    phase = registry_of(templates, towns, sample).formats["sample-cup"].phases[0]
    assert coinflip_announcement("<@1>", "<@2>", phase) == (
        "Coinflip: <@1> wins and is A, so <@1> bans first. <@2> is B."
    )


def test_only_modes_that_can_start_matches_are_offered(sample, old, templates, towns):
    reg = registry_of(templates, towns, sample, old)
    assert mode_choices(reg, "") == [("Sample Cup", "sample-cup")]
    assert mode_choices(reg, "old") == []


def test_templates_are_offered_only_for_agreed_phases(sample, ranked, templates, towns):
    reg = registry_of(templates, towns, sample, ranked)
    assert template_choices(reg, "sample-cup", None, "") == []
    assert template_choices(reg, "ranked", None, "") == [("Jebus Cross", "JC"), ("6lm10a", "6lm10a")]
    assert template_choices(reg, "ranked", "Open", "jeb") == [("Jebus Cross", "JC")]
    assert template_choices(reg, "nope", None, "") == []


# --- /match status ---------------------------------------------------------------------------------------


def status_of(registry, records, monkeypatch):
    async def guarded(interaction):
        return records

    monkeypatch.setattr(match, "guarded_records", guarded)
    it = interaction(registry, None)
    asyncio.run(match.status.callback(it))
    return it.followup.send.await_args.args[0]


def started_match():
    return [
        make_record(1, "match_started", p1=1, p2=2, mode="sample-cup", phase="Main", template=None),
        make_record(2, "coinflip", winner=2),
    ]


def test_status_shows_the_match_the_selection_and_the_records(sample, templates, towns, monkeypatch):
    text = status_of(registry_of(templates, towns, sample), started_match(), monkeypatch)
    assert "Coinflip: <@2> is A (acts first), <@1> is B" in text
    assert "Template Selection: step 1 of 2, <@2> bans" in text
    assert "Game 1: not decided yet" in text
    assert "I read 2 record(s) in this thread:" in text


def test_status_leaves_the_record_list_out_when_it_would_not_fit(sample, templates, towns, monkeypatch):
    monkeypatch.setattr(match, "MAX_REPLY", 50)
    text = status_of(registry_of(templates, towns, sample), started_match(), monkeypatch)
    assert "Coinflip:" in text and "I read" not in text


def test_status_explains_a_thread_it_cannot_trust(sample, templates, towns, monkeypatch):
    records = started_match() + [make_record(3, "trade_started", game=1, pair=("castle", "tower"))]
    text = status_of(registry_of(templates, towns, sample), records, monkeypatch)
    assert text.startswith("I can't read this thread:") and "game 1 is not decided" in text
