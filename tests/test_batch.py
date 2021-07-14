"""Tests for for the decorator dike.batch"""
import asyncio
import random

import pytest

import dike


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


def test_upstream_exception_is_propagated_to_all_callers():
    @dike.batch(target_batch_size=3, max_waiting_time=10)
    async def f(arg1, arg2):
        assert arg1 == [0, 1, 2]
        assert arg2 == ["a", "b", "c"]
        raise RuntimeError("Upstream exception")

    async def run_test():
        results = await asyncio.wait_for(
            asyncio.gather(
                f([0], ["a"]),
                f([1], ["b"]),
                f([2], ["c"]),
                return_exceptions=True
            ),
            timeout=1.0,
        )
        for r in results:
            assert isinstance(r, Exception)
            # assert str(r) == "Upstream exception"

    asyncio.run(run_test())


def test_concurrent_calculations_do_not_clash():
    """Run many calculations in parallel and see if the results are always correct"""

    @dike.batch(target_batch_size=3, max_waiting_time=0.01)
    async def f(arg):
        print("Batch size", len(arg))
        await asyncio.sleep(random.random() / 100.0)
        return [x * 2 for x in arg]

    async def do_n_calculations(n):
        for _ in range(n):
            number = random.randint(0, 2 ** 20)
            result = await (f([number]))
            assert result[0] == number * 2

            await asyncio.sleep(random.random() / 10.0)

    async def run_test():
        await asyncio.gather(*[do_n_calculations(20) for _ in range(5)])

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
