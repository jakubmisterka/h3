import asyncio

import pytest

from locks import thread_lock


def test_a_thread_always_gets_the_same_lock():
    assert thread_lock(1001) is thread_lock(1001)


def test_different_threads_get_different_locks():
    assert thread_lock(1002) is not thread_lock(1003)


async def read_check_post(thread_id, log, name, delay):
    """What a command does: read the state, wait on Discord, then post based on what it read."""
    async with thread_lock(thread_id):
        seen = len(log)  # read the thread
        await asyncio.sleep(delay)  # waiting on Discord: this is where another command could slip in
        log.append((name, seen))  # post


@pytest.mark.asyncio
async def test_two_commands_in_one_thread_run_one_after_the_other():
    log = []
    await asyncio.gather(read_check_post(2001, log, "first", 0.05), read_check_post(2001, log, "second", 0))
    # the second command only read the thread after the first had posted
    assert log == [("first", 0), ("second", 1)]


@pytest.mark.asyncio
async def test_without_the_lock_both_would_have_read_the_same_old_state():
    log = []

    async def unlocked(name, delay):
        seen = len(log)
        await asyncio.sleep(delay)
        log.append((name, seen))

    await asyncio.gather(unlocked("first", 0.05), unlocked("second", 0))
    assert sorted(seen for _, seen in log) == [0, 0]  # the problem the lock prevents


@pytest.mark.asyncio
async def test_commands_in_different_threads_do_not_wait_for_each_other():
    log = []
    await asyncio.gather(read_check_post(3001, log, "slow", 0.05), read_check_post(3002, log, "quick", 0))
    assert [name for name, _ in log] == ["quick", "slow"]


@pytest.mark.asyncio
async def test_the_lock_is_released_when_a_command_fails():
    with pytest.raises(RuntimeError):
        async with thread_lock(4001):
            raise RuntimeError("refused")
    assert not thread_lock(4001).locked()
