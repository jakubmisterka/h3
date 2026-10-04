import asyncio

from locks import ThreadLocks


async def test_commands_on_one_thread_run_one_after_the_other():
    locks = ThreadLocks()
    log = []

    async def command(name):
        async with locks.hold(1):
            log.append(f"{name} start")
            await asyncio.sleep(0.01)
            log.append(f"{name} end")

    await asyncio.gather(command("first"), command("second"))
    assert log == ["first start", "first end", "second start", "second end"]


async def test_different_threads_do_not_wait_for_each_other():
    locks = ThreadLocks()
    both_inside = asyncio.Event()
    inside = 0

    async def command(thread_id):
        nonlocal inside
        async with locks.hold(thread_id):
            inside += 1
            if inside == 2:
                both_inside.set()
            await asyncio.wait_for(both_inside.wait(), timeout=1)

    await asyncio.gather(command(1), command(2))


async def test_lock_is_forgotten_when_nobody_waits():
    locks = ThreadLocks()
    async with locks.hold(7):
        assert 7 in locks._entries
    assert locks._entries == {}


async def test_lock_is_released_when_a_command_fails():
    locks = ThreadLocks()
    try:
        async with locks.hold(3):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    async with locks.hold(3):
        pass
