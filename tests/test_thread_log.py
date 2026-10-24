"""Tests ThreadLog with a fake thread, so no connection to Discord is needed."""

import asyncio
from types import SimpleNamespace

import pytest

from discord_commands.thread_log import ThreadLog
from state import RecordError, make_record

BOT, ANNA = 7, 111


class FakeThread:
    def __init__(self, messages=()):
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
