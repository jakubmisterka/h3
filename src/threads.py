"""The Discord side of match state: read events from a thread and post new ones.

Each event lives in an embed footer of one of the bot's own messages, next to the
text players read. Reading the bot's own messages needs no privileged intent, but
the bot must be allowed to read message history in the thread.
"""

import discord

from state import Event, decode, encode, make_event


class ThreadLog:
    """The event log of one match thread."""

    def __init__(self, thread: discord.Thread, bot_id: int):
        self.thread = thread
        self.bot_id = bot_id
        self.last_n = 0

    async def read(self) -> list[Event]:
        """All events in the thread, oldest first. Messages by other users are ignored."""
        events = []
        async for message in self.thread.history(limit=None, oldest_first=True):
            if message.author.id != self.bot_id:
                continue
            for embed in message.embeds:
                if embed.footer and embed.footer.text:
                    event = decode(embed.footer.text)
                    if event is not None:
                        events.append(event)
        self.last_n = events[-1].n if events else 0
        return events

    async def say(self, text: str, *, ping: str | None = None) -> None:
        """Post a message that is not an event (for example a status report)."""
        await self.thread.send(content=ping, embed=discord.Embed(description=text))

    async def post(self, type: str, text: str, *, ping: str | None = None, **data) -> Event:
        """Post the next event with its readable text. Call read() first when continuing a match.

        `ping` is plain message text placed above the embed (embeds do not notify anyone),
        for example the mentions of the players whose turn it is.
        """
        event = make_event(self.last_n + 1, type, **data)
        embed = discord.Embed(description=text)
        embed.set_footer(text=encode(event))
        await self.thread.send(content=ping, embed=embed)
        self.last_n = event.n
        return event
