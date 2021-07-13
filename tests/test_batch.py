import asyncio
from typing import Dict
import dike
import pytest


async def raise_error(message):
    raise RuntimeError(message)


def test_single_items_batchsize_reached():
    @dike.batch(target_batch_size=3, max_waiting_time=10)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2]
        assert arg2 == ["a", "b", "c"]
        return [10, 11, 12]

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f([0], ["a"]),
                f([1], ["b"]),
                f([2], ["c"]),
            ),
            timeout=1.0,
        )

        assert result == [[10], [11], [12]]

    asyncio.run(run_test())


def test_single_items_kwargs_batchsize_reached():
    @dike.batch(target_batch_size=3, max_waiting_time=10)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2]
        assert arg2 == ["a", "b", "c"]
        return [10, 11, 12]

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f(arg1=[0], arg2=["a"]),
                f(arg1=[1], arg2=["b"]),
                f(arg2=["c"], arg1=[2]),
            ),
            timeout=1.0,
        )

        assert result == [[10], [11], [12]]

    asyncio.run(run_test())


def test_single_items_timeout():
    @dike.batch(target_batch_size=10, max_waiting_time=0.01)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2]
        assert arg2 == ["a", "b", "c"]
        return [10, 11, 12]

    async def run_test():
        tasks = asyncio.gather(
            f([0], ["a"]),
            f([1], ["b"]),
            f([2], ["c"]),
        )
        result = await asyncio.wait_for(tasks, timeout=0.2)

        assert result == [[10], [11], [12]]

    asyncio.run(run_test())


def test_multi_batch_size_reached():
    @dike.batch(target_batch_size=5, max_waiting_time=2)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2, 3, 4]
        assert arg2 == ["a", "b", "c", "d", "e"]
        return [10, 11, 12, 13, 14]

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f([0], ["a"]),
                f([1, 2, 3], ["b", "c", "d"]),
                f([4], ["e"]),
            ),
            timeout=0.1,
        )

        assert result == [[10], [11, 12, 13], [14]]

    asyncio.run(run_test())


def test_multi_args_and_kwargs_batch_size_reached():
    @dike.batch(target_batch_size=5, max_waiting_time=2)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2, 3, 4]
        assert arg2 == ["a", "b", "c", "d", "e"]
        return [10, 11, 12, 13, 14]

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f([0], arg2=["a"]),
                f([1, 2, 3], arg2=["b", "c", "d"]),
                f([4], arg2=["e"]),
            ),
            timeout=0.1,
        )

        assert result == [[10], [11, 12, 13], [14]]

    asyncio.run(run_test())


def test_multi_item_timeout():
    @dike.batch(target_batch_size=10, max_waiting_time=0.01)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2, 3, 4]
        assert arg2 == ["a", "b", "c", "d", "e"]
        return [10, 11, 12, 13, 14]

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f([0], ["a"]),
                f([1, 2, 3], ["b", "c", "d"]),
                f([4], ["e"]),
            ),
            timeout=0.2,
        )

        assert result == [[10], [11, 12, 13], [14]]

    asyncio.run(run_test())


def test_items_running_over_batch_size():
    @dike.batch(target_batch_size=5, max_waiting_time=2)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2, 3, 4, 5]
        assert arg2 == ["a", "b", "c", "d", "e", "f"]
        return [10, 11, 12, 13, 14, 15]

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f([0], ["a"]),
                f([1, 2, 3], ["b", "c", "d"]),
                f([4, 5], ["e", "f"]),
            ),
            timeout=0.1,
        )

        assert result == [[10], [11, 12, 13], [14, 15]]

    asyncio.run(run_test())


def test_upstream_exception_is_propagated():
    @dike.batch(target_batch_size=3, max_waiting_time=10)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2]
        assert arg2 == ["a", "b", "c"]
        raise RuntimeError("Upstream exception")

    async def run_test():
        with pytest.raises(RuntimeError, match="Upstream exception"):
            await asyncio.wait_for(
                asyncio.gather(
                    f([0], ["a"]),
                    f([1], ["b"]),
                    f([2], ["c"]),
                ),
                timeout=1.0,
            )

    asyncio.run(run_test())


def test_concurrent_calculations_do_not_clash():
    n_calls_to_f = 0
    fire_second_call = None

    @dike.batch(target_batch_size=3, max_waiting_time=0.1)
    async def f(arg1):
        nonlocal n_calls_to_f
        if n_calls_to_f == 0:
            n_calls_to_f += 1
            assert arg1 == [1, 2, 3]
            await fire_second_call.wait()
            return [11, 12, 13]

        assert arg1 == [4, 5, 6]
        return [14, 15, 16]

    async def run_test():
        nonlocal fire_second_call
        fire_second_call = asyncio.Event()

        task_1 = asyncio.create_task(f([1, 2, 3]))
        task_2 = asyncio.create_task(f([4, 5, 6]))
        await asyncio.sleep(0.01)
        fire_second_call.set()

        await task_1
        assert task_1.result() == [11, 12, 13]
        await task_1
        assert task_2.result() == [14, 15, 16]

    asyncio.run(run_test())


@pytest.mark.parametrize("batch_size", [0, -1, float("-inf")])
def test_illegal_batch_size_leads_to_value_error(batch_size):
    with pytest.raises(ValueError):

        @dike.batch(target_batch_size=batch_size, max_waiting_time=1)
        async def f(arg1):
            pass


@pytest.mark.parametrize("waiting_time", [0, -1, float("-inf")])
def test_illegal_waiting_time_leads_to_value_error(waiting_time):
    with pytest.raises(ValueError):

        @dike.batch(target_batch_size=1, max_waiting_time=waiting_time)
        async def f(arg1):
            pass
