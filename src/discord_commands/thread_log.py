"""Writing records into a match thread and reading them back.

Every step of a match is one message from the bot. It starts with a tag and goes on with the
text players read, for example

    [#1 ms] Match started: <@111> vs <@222>. This is your match thread.

The tag and the rules for reading the data out of the text are in `state.py`. To know where a
match stands, the bot reads the thread's history and parses its own messages; messages from
other users, and bot messages without a tag, are ignored. Reading history needs the
"Read Message History" permission.

Suggestions while a player is typing (autocomplete) read the thread on every keystroke and must be answered
within 3 seconds, or Discord drops them ("Unknown interaction"). For those only, `records_for_autocomplete`
keeps the parsed records for a few seconds, and gives up after 2. The commands themselves always read the thread.
"""

import asyncio
import logging
import time

import discord

from state import Record, RecordError, make_record, parse, tag


logger = logging.getLogger("h3bot")

AUTOCOMPLETE_TIMEOUT = 2.0  # seconds; Discord allows an autocomplete 3 seconds to answer
AUTOCOMPLETE_CACHE_SECONDS = 10.0  # suggestions may be this old; the bot's own posts clear them at once
_cache: dict[int, tuple[float, list[Record]]] = {}  # thread id -> (when read, its records)


def forget_cached_records(thread_id: int | None = None) -> None:
    """Drop the remembered records of a thread, or of all threads."""
    if thread_id is None:
        _cache.clear()
    else:
        _cache.pop(thread_id, None)


async def records_for_autocomplete(thread: discord.Thread, bot_id: int) -> list[Record] | None:
    """The records of a thread for suggestions: recent ones from memory, else read within the time Discord allows.

    None means they could not be read in time; the caller then offers no suggestions.
    """
    now = time.monotonic()
    cached = _cache.get(thread.id)
    if cached is not None and now - cached[0] < AUTOCOMPLETE_CACHE_SECONDS:
        return cached[1]
    try:
        records = await asyncio.wait_for(ThreadLog(thread, bot_id).read(), AUTOCOMPLETE_TIMEOUT)
    except TimeoutError:
        logger.warning("Reading thread %s took more than %s s, so autocomplete offered nothing", thread.id, AUTOCOMPLETE_TIMEOUT)
        return None
    for thread_id in [t for t, (when, _) in _cache.items() if now - when >= AUTOCOMPLETE_CACHE_SECONDS]:
        del _cache[thread_id]  # do not remember finished matches forever
    _cache[thread.id] = (now, records)
    return records


class ThreadLog:
    """The records of one match thread."""

    def __init__(self, thread: discord.Thread, bot_id: int):
        self.thread = thread
        self.bot_id = bot_id
        self.last_n = 0  # number of the latest record seen or posted

    async def read(self) -> list[Record]:
        """All records in the thread, oldest first."""
        records = []
        async for message in self.thread.history(limit=None, oldest_first=True):
            if message.author.id != self.bot_id:
                continue
            record = parse(message.content)
            if record is not None:
                records.append(record)
        self.last_n = records[-1].n if records else 0
        return records

    async def post(self, type: str, text: str, game: int | None = None, **data) -> Record:
        """Post the next record as a message: the tag, then `text`.

        `text` is what players read. It must contain the data of the record where the reading
        rules look for it (see `state.py`), for example both players mentioned in order for
        a match start. Mentioning people in it notifies them. Call `read()` first when
        continuing an existing match, so the numbering carries on. `game` marks a record of one game's trade.
        """
        record = make_record(self.last_n + 1, type, game, **data)
        content = f"{tag(record)} {text}"
        # Make sure the message reads back as exactly this record, before anyone sees it.
        if parse(content) != record:
            raise RecordError(f"the text of this {type!r} message does not contain its data in the expected order")
        await self.thread.send(content)
        forget_cached_records(self.thread.id)  # what suggestions know is old now
        self.last_n = record.n
        return record
