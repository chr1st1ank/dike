"""Tests for for the decorator dike.batch"""
# pylint: disable=missing-function-docstring
import asyncio
import importlib
import inspect
import random
import sys

import numpy as np
import pytest

import dike


def exceptions_equal(exception1, exception2):
    """Returns True if the exceptions have the same type and message"""
    # pylint: disable=unidiomatic-typecheck
    return type(exception1) == type(exception2) and str(exception1) == str(exception2)


async def raise_error(message):
    raise RuntimeError(message)


@pytest.mark.parametrize("argtype_converter, arg_type_name", [(list, "list"), (np.array, "numpy")])
def test_single_items_batchsize_reached(argtype_converter, arg_type_name):
    @dike.batch(target_batch_size=3, max_waiting_time=10, argument_type=arg_type_name)
    async def f(arg1, arg2):
        assert list(arg1) == [0, 1, 2]
        assert list(arg2) == ["a", "b", "c"]
        return argtype_converter([10, 11, 12])

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f(argtype_converter([0]), argtype_converter(["a"])),
                f(argtype_converter([1]), argtype_converter(["b"])),
                f(argtype_converter([2]), argtype_converter(["c"])),
            ),
            timeout=1.0,
        )

        assert all(isinstance(r, type(argtype_converter([]))) for r in result)
        assert list(map(list, result)) == [[10], [11], [12]]

    asyncio.run(run_test())


@pytest.mark.parametrize("argtype_converter, arg_type_name", [(list, "list"), (np.array, "numpy")])
def test_single_items_kwargs_batchsize_reached(argtype_converter, arg_type_name):
    @dike.batch(target_batch_size=3, max_waiting_time=10, argument_type=arg_type_name)
    async def f(arg1, arg2):
        assert list(arg1) == [0, 1, 2]
        assert list(arg2) == ["a", "b", "c"]
        return argtype_converter([10, 11, 12])

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f(arg2=argtype_converter(["a"]), arg1=argtype_converter([0])),
                f(arg2=argtype_converter(["b"]), arg1=argtype_converter([1])),
                f(arg1=argtype_converter([2]), arg2=argtype_converter(["c"])),
            ),
            timeout=1.0,
        )

        assert all(isinstance(r, type(argtype_converter([]))) for r in result)
        assert list(map(list, result)) == [[10], [11], [12]]

    asyncio.run(run_test())


@pytest.mark.parametrize("argtype_converter, arg_type_name", [(list, "list"), (np.array, "numpy")])
def test_single_items_mixed_kwargs_raises_value_error(argtype_converter, arg_type_name):
    @dike.batch(target_batch_size=3, max_waiting_time=0.01, argument_type=arg_type_name)
    async def f(arg1, arg2):
        assert list(arg1) == [0, 1]
        assert list(arg2) == ["a", "b"]
        return argtype_converter([10, 11])

    async def run_test():
        result = await asyncio.wait_for(
            asyncio.gather(
                f(argtype_converter([0]), argtype_converter(["a"])),
                f(argtype_converter([1]), argtype_converter(["b"])),
                f(arg2=argtype_converter(["c"]), arg1=argtype_converter([2])),
                f(argtype_converter([1])),  # pylint: disable=no-value-for-parameter
                f(argtype_converter([]), argtype_converter([])),
                return_exceptions=True,
            ),
            timeout=1.0,
        )

        assert all(isinstance(r, type(argtype_converter([]))) for r in result[:2])
        assert list(result[0]) == [10]
        assert list(result[1]) == [11]
        assert exceptions_equal(
            result[2], ValueError("Inconsistent use of positional and keyword arguments")
        )
        assert exceptions_equal(
            result[3], ValueError("Inconsistent use of positional and keyword arguments")
        )
        assert exceptions_equal(
            result[4], ValueError("Function called with empty collections as arguments")
        )

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
            asyncio.gather(f([0], ["a"]), f([1], ["b"]), f([2], ["c"]), return_exceptions=True),
            timeout=1.0,
        )
        for r in results:
            assert isinstance(r, RuntimeError)
            assert str(r) == "Upstream exception"

    asyncio.run(run_test())


def test_concurrent_calculations_do_not_clash():
    """Run many calculations in parallel and see if the results are always correct"""

    @dike.batch(target_batch_size=3, max_waiting_time=0.01)
    async def f(arg):
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


def test_no_numpy_available(monkeypatch):
    """Test if without numpy the decorator works normally but refuses to use numpy"""
    monkeypatch.setitem(sys.modules, "numpy", None)
    importlib.reload(dike._batch)  # pylint: disable=protected-access

    with pytest.raises(ValueError, match="Unable to use .*numpy.*"):

        @dike.batch(target_batch_size=3, max_waiting_time=10, argument_type="numpy")
        def g(_):
            pass

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


@pytest.mark.parametrize("batch_size", [0, -1, float("-inf")])
def test_illegal_batch_size_leads_to_value_error(batch_size):
    with pytest.raises(ValueError):

        @dike.batch(target_batch_size=batch_size, max_waiting_time=1)
        async def f(_):
            pass


@pytest.mark.parametrize("waiting_time", [0, -1, float("-inf")])
def test_illegal_waiting_time_leads_to_value_error(waiting_time):
    with pytest.raises(ValueError):

        @dike.batch(target_batch_size=1, max_waiting_time=waiting_time)
        async def f(_):
            pass


@pytest.mark.parametrize("argument_type", ["", "unknown"])
def test_illegal_argument_type_leads_to_value_error(argument_type):
    with pytest.raises(ValueError):

        @dike.batch(target_batch_size=1, max_waiting_time=1, argument_type=argument_type)
        async def f(_):
            pass


def test_internal_storage_is_cleaned():
    @dike.batch(target_batch_size=3, max_waiting_time=10)
    async def f(*_):
        return [10, 11, 12]

    async def run_test():
        task1 = asyncio.create_task(f([0]))
        task2 = asyncio.create_task(f([0]))
        task3 = asyncio.create_task(f([0]))
        results = await asyncio.gather(task1, task2, task3)
        assert results == [[10], [11], [12]]

        # Check if the internal dictionaries are empty (there are no other batches here)
        closure_vars = inspect.getclosurevars(f).nonlocals
        assert not closure_vars["results"]
        assert not closure_vars["num_results_ready"]
        assert not closure_vars["result_ready_events"]
        assert not closure_vars["call_args_queue"]
        assert not closure_vars["n_rows_in_queue"]

    asyncio.run(run_test())


def test_internal_storage_is_cleaned_also_when_cancelled():
    @dike.batch(target_batch_size=3, max_waiting_time=0.01)
    async def f(*_):
        return [10, 11, 12]

    async def run_test():
        task1 = asyncio.create_task(f([0]))
        await asyncio.sleep(0)
        task2 = asyncio.create_task(f([0]))
        task3 = asyncio.create_task(f([0]))
        task1.cancel()
        result2 = await task2
        result3 = await task3
        assert result2, result3 == ([11], [12])

        # Check if the internal dictionaries are empty (there are no other batches here)
        closure_vars = inspect.getclosurevars(f).nonlocals
        assert not closure_vars["results"]
        assert not closure_vars["num_results_ready"]
        assert not closure_vars["result_ready_events"]
        assert not closure_vars["call_args_queue"]
        assert not closure_vars["n_rows_in_queue"]

    asyncio.run(run_test())
