"""Writing records into a match thread and reading them back.

Every step of a match is one message from the bot. It starts with a tag and goes on with the
text players read, for example

    [#1 ms] Match started: <@111> vs <@222>. This is your match thread.

The tag and the rules for reading the data out of the text are in `state.py`. To know where a
match stands, the bot reads the thread's history and parses its own messages; messages from
other users, and bot messages without a tag, are ignored. Reading history needs the
"Read Message History" permission.
"""

import discord

from state import Record, RecordError, make_record, parse, tag


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

    async def post(self, type: str, text: str, **data) -> Record:
        """Post the next record as a message: the tag, then `text`.

        `text` is what players read. It must contain the data of the record where the reading
        rules look for it (see `state.py`), for example both players mentioned in order for
        a match start. Mentioning people in it notifies them. Call `read()` first when
        continuing an existing match, so the numbering carries on.
        """
        record = make_record(self.last_n + 1, type, **data)
        content = f"{tag(record)} {text}"
        # Make sure the message reads back as exactly this record, before anyone sees it.
        if parse(content) != record:
            raise RecordError(f"the text of this {type!r} message does not contain its data in the expected order")
        await self.thread.send(content)
        self.last_n = record.n
        return record
