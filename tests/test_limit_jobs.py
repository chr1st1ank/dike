"""Tests for the dike.limit_jobs decorator"""
# pylint: disable=missing-function-docstring
import asyncio
import re

import parametrized
import pytest

import dike

concurrency_limit = parametrized.fixture(3, 1, 0, -1, 1.5)


@dike.limit_jobs(limit=2)
async def block_until_released(event: asyncio.Event, arg):
    """Blocks until the given event is sent and then returns arg"""
    await event.wait()
    return arg


@pytest.mark.parametrize("l", [1, 2, 3, 2.5, float("inf")])
def test_simple_usage(l):
    """Simply wrap a coroutine with different limits and call it once"""

    @dike.limit_jobs(limit=l)
    async def f():
        pass

    asyncio.run(f())


def test_single_calls():
    """Try single calls to the wrapped function"""

    async def testloop():
        for i in range(4):
            event = asyncio.Event()
            event.set()
            assert (await block_until_released(event, i)) == i

    asyncio.run(testloop())


def test_calls_below_limit():
    """Some simultaneous calls below the threshold should be processed normally"""

    async def testloop():
        event = asyncio.Event()
        tasks = asyncio.gather(
            block_until_released(event, 1),
            block_until_released(event, 2),
        )
        await asyncio.sleep(0)  # Give limit_jobs a chance to check the number of calls
        event.set()  # Make the tasks terminate on await
        assert (await tasks) == [1, 2]

    asyncio.run(testloop())


def test_calls_exceeding_limit():
    """Too many simultaneous calls should raise a TooManyCalls exception"""

    async def testloop():
        event = asyncio.Event()
        tasks = asyncio.gather(
            block_until_released(event, 1),
            block_until_released(event, 2),
            block_until_released(event, 3),
        )
        with pytest.raises(
            dike.TooManyCalls,
            match="Too many calls to function block_until_released! limit=2 exceeded",
        ):
            assert (await tasks) == [1, 2, 3]

    asyncio.run(testloop())


def test_call_with_limit_0():
    """Limit of 0 is allowed to create a "forbidden" call"""

    @dike.limit_jobs(limit=0)
    async def f():
        pass

    with pytest.raises(dike.TooManyCalls):
        asyncio.run(f())


@pytest.mark.parametrize("l", [-1, -1.5, float("-inf")])
def test_unlogical_limits_give_clear_error(l):
    """Ensure that a proper error message is shown when trying to set strange limits"""
    with pytest.raises(ValueError, match=re.escape("Error when wrapping f(). Limit must be >= 0")):

        @dike.limit_jobs(limit=l)
        async def f():
            pass


def test_function_instead_coroutine():
    """Ensure that a proper error message is shown when trying to wrap a blocking function"""
    with pytest.raises(ValueError, match="Error when wrapping .+ Only coroutines can be wrapped"):

        @dike.limit_jobs(limit=5)
        def f():
            pass
