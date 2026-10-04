"""One lock per match thread, so two commands on the same match never overlap."""

import asyncio
from contextlib import asynccontextmanager


class ThreadLocks:
    def __init__(self) -> None:
        self._entries: dict[int, list] = {}  # thread id -> [lock, number of users]

    @asynccontextmanager
    async def hold(self, thread_id: int):
        """Wait for this thread's turn. Other threads are not affected."""
        entry = self._entries.setdefault(thread_id, [asyncio.Lock(), 0])
        entry[1] += 1
        try:
            async with entry[0]:
                yield
        finally:
            entry[1] -= 1
            if entry[1] == 0:
                del self._entries[thread_id]  # nobody waits: forget the lock
