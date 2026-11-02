"""One lock per match thread, so two commands in the same thread never run their read-check-post at the same time.

A command reads the thread, checks that it may act, and posts its record. Between those steps the bot
waits on Discord, and meanwhile another command in the same thread could read the same old state and
also pass its check (for example one player sending `/ban` twice). Taking this thread's lock first makes
the second command wait until the first has posted, and then read the thread including that record.

Other threads have their own locks, so matches never wait for each other. The locks live in the bot's
memory, which is enough for one bot process: after a restart nothing is in flight anyway.
"""

import asyncio

_locks: dict[int, asyncio.Lock] = {}  # thread id -> its lock


def thread_lock(thread_id: int) -> asyncio.Lock:
    """The lock of one thread. Use it as `async with thread_lock(thread.id): ...`."""
    if thread_id not in _locks:
        _locks[thread_id] = asyncio.Lock()
    return _locks[thread_id]
