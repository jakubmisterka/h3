"""Tests ThreadLog with a fake thread, so no connection to Discord is needed."""

import asyncio
from types import SimpleNamespace

import pytest

from discord_commands.thread_log import ThreadLog
from state import RecordError, make_record

BOT, ANNA = 7, 111


class FakeThread:
    def __init__(self, messages=(), thread_id=1):
        self.id = thread_id
        self.messages = list(messages)
        self.sent = []  # the text of everything posted

    def history(self, limit=None, oldest_first=False):
        async def messages():
            for message in self.messages:
                yield message

        return messages()

    async def send(self, content):
        self.sent.append(content)


def message(author_id, content):
    return SimpleNamespace(author=SimpleNamespace(id=author_id), content=content)


def bot_record(n):
    """A record message as the bot posts it."""
    return message(BOT, f"[#{n} cf] Coinflip: <@1> wins.")


def numbers(thread):
    return [r.n for r in asyncio.run(ThreadLog(thread, BOT).read())]


def test_post_sends_one_message_starting_with_the_tag():
    thread = FakeThread()
    record = asyncio.run(ThreadLog(thread, BOT).post("coinflip", "Coinflip: <@1> wins.", winner=1))

    assert thread.sent == ["[#1 cf] Coinflip: <@1> wins."]
    assert record.n == 1


def test_what_was_posted_can_be_read_back():
    thread = FakeThread()
    posted = asyncio.run(ThreadLog(thread, BOT).post("coinflip", "Anna <@1> wins against <@2>", winner=1))
    thread.messages = [message(BOT, content) for content in thread.sent]
    assert asyncio.run(ThreadLog(thread, BOT).read()) == [posted]


def test_text_that_does_not_contain_the_data_is_not_sent():
    thread = FakeThread()
    with pytest.raises(RecordError, match="does not contain its data"):
        asyncio.run(ThreadLog(thread, BOT).post("coinflip", "Coinflip: <@2> wins.", winner=1))
    with pytest.raises(RecordError):
        asyncio.run(ThreadLog(thread, BOT).post("coinflip", "Coinflip: nobody wins.", winner=1))
    assert thread.sent == []


def test_numbering_continues_after_reading():
    thread = FakeThread([bot_record(1), bot_record(2)])
    log = ThreadLog(thread, BOT)
    asyncio.run(log.read())
    assert asyncio.run(log.post("coinflip", "<@1> wins", winner=1)).n == 3


def test_numbering_continues_after_posting():
    log = ThreadLog(FakeThread(), BOT)
    first = asyncio.run(log.post("coinflip", "<@1> wins", winner=1))
    second = asyncio.run(log.post("coinflip", "<@1> wins", winner=1))
    assert (first.n, second.n) == (1, 2)


def test_read_returns_records_oldest_first():
    assert numbers(FakeThread([bot_record(1), bot_record(2)])) == [1, 2]


def test_messages_from_players_are_ignored_even_if_they_look_like_records():
    forged = message(ANNA, "[#2 cf] Coinflip: <@9> wins.")
    assert numbers(FakeThread([bot_record(1), forged, message(ANNA, "hello")])) == [1]


def test_bot_messages_without_a_tag_are_ignored():
    thread = FakeThread([message(BOT, "Good luck, both!"), message(BOT, ""), bot_record(1)])
    assert numbers(thread) == [1]


def test_empty_thread_has_no_records_and_starts_at_one():
    log = ThreadLog(FakeThread(), BOT)
    assert asyncio.run(log.read()) == []
    assert asyncio.run(log.post("coinflip", "<@1> wins", winner=1)).n == 1


def test_a_record_of_a_game_is_posted_with_the_marker_and_read_back():
    thread = FakeThread()
    posted = asyncio.run(ThreadLog(thread, BOT).post("coinflip", "Coinflip: <@1> wins.", game=2, winner=1))
    assert thread.sent == ["[#1 cf g2] Coinflip: <@1> wins."]
    thread.messages = [message(BOT, content) for content in thread.sent]
    assert asyncio.run(ThreadLog(thread, BOT).read()) == [posted]


# --- suggestions while typing --------------------------------------------------------------------------------------

import discord_commands.thread_log as thread_log  # noqa: E402  (kept with the tests that use it)


@pytest.fixture(autouse=True)
def empty_cache():
    thread_log.forget_cached_records()
    yield
    thread_log.forget_cached_records()


class CountingThread(FakeThread):
    """A thread that counts how often its history is read, and can be slow."""

    def __init__(self, *args, delay=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads = 0
        self.delay = delay

    def history(self, limit=None, oldest_first=False):
        self.reads += 1

        async def messages():
            await asyncio.sleep(self.delay)
            for message in self.messages:
                yield message

        return messages()


def suggestions(thread):
    return asyncio.run(thread_log.records_for_autocomplete(thread, BOT))


def test_recent_records_are_not_read_again_for_the_next_keystroke():
    thread = CountingThread([bot_record(1)])
    first = suggestions(thread)
    second = suggestions(thread)
    assert first == second and thread.reads == 1


def test_records_are_read_again_once_they_are_old(monkeypatch):
    thread = CountingThread([bot_record(1)])
    clock = [1000.0]
    monkeypatch.setattr(thread_log.time, "monotonic", lambda: clock[0])
    suggestions(thread)
    clock[0] += thread_log.AUTOCOMPLETE_CACHE_SECONDS + 1
    suggestions(thread)
    assert thread.reads == 2


def test_a_post_by_the_bot_makes_the_remembered_records_old():
    thread = CountingThread([bot_record(1)])
    suggestions(thread)
    asyncio.run(ThreadLog(thread, BOT).post("coinflip", "Coinflip: <@1> wins.", winner=1))
    thread.messages = [message(BOT, content) for content in thread.sent]
    assert [r.n for r in suggestions(thread)] == [1]  # read again, so it sees what was just posted
    assert thread.reads == 2


def test_each_thread_has_its_own_remembered_records():
    one, other = CountingThread([bot_record(1)], thread_id=1), CountingThread([bot_record(1)], thread_id=2)
    suggestions(one)
    suggestions(other)
    assert (one.reads, other.reads) == (1, 1)


def test_a_read_that_takes_too_long_gives_up_instead_of_waiting(monkeypatch, caplog):
    monkeypatch.setattr(thread_log, "AUTOCOMPLETE_TIMEOUT", 0.05)
    thread = CountingThread([bot_record(1)], delay=5)
    with caplog.at_level("WARNING", logger="h3bot"):
        assert suggestions(thread) is None
    assert "took more than" in caplog.text


def test_a_failed_read_is_not_remembered(monkeypatch):
    monkeypatch.setattr(thread_log, "AUTOCOMPLETE_TIMEOUT", 0.05)
    slow = CountingThread([bot_record(1)], delay=5)
    suggestions(slow)
    slow.delay = 0
    assert [r.n for r in suggestions(slow)] == [1]
