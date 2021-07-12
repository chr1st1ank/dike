import asyncio
import concurrent
import functools
import inspect
from dataclasses import dataclass
from typing import Callable, List, Sequence, Iterable, Awaitable, Union, Dict


def wrap_in_coroutine(func: Callable) -> Callable:
    """Decorator to wrap a function into a coroutine function.

    If `func` is already a coroutine function it is returned as-is.

    Args:
        func: A callable object (function or coroutine function)

    Returns:
        A coroutine function which executes `func`.
    """
    if inspect.iscoroutinefunction(func):
        return func

    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return _wrapper


class TooManyCalls(Exception):
    pass


def limit_jobs(*, limit: int):
    """Decorator to limit the number of concurrent calls to a coroutine function.

    Args:
        limit: The maximum number of ongoing calls allowed at any time

    Returns:
        The given coroutine function with added concurrency protection

    Raises:
        TooManyCalls: The decorated function raises a decoweb.ToomanyCalls exception
            if it is called while already running `limit` times concurrently.
    """
    if not limit >= 0:
        raise ValueError("Error when wrapping f(). Limit must be >= 0!")
    counter = limit

    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Error when wrapping {str(func)}. Only coroutines can be wrapped!")

        @functools.wraps(func)
        async def limited_call(*args, **kwargs):
            nonlocal counter
            if counter == 0:
                raise TooManyCalls(f"Too many calls to {str(func)}! {limit=}")
            try:
                counter -= 1
                return await func(*args, **kwargs)
            finally:
                counter += 1

        return limited_call

    return decorator


# TODO: Support for some non-batchable arguments to group by
# TODO: Support for kwargs
# def batch(*, batch_args: Iterable[str], target_batch_size: int, max_waiting_time: float):
def batch(*, target_batch_size: int, max_waiting_time: float):
    """Calculate in batches.


    Assumptions:  # TODO: Add assertions and tests
        - The return value of the wrapped function is a single iterable
        - All calls to the underlying function have the same number of positional arguments
    """
    if not target_batch_size > 0:
        raise ValueError(f"target_batch_size must be > 0, but got {target_batch_size}")
    if not max_waiting_time > 0:
        raise ValueError(f"max_waiting_time must be > 0, but got {max_waiting_time}")

    def decorator(func):
        batch_no: int = 0
        queue = []
        n_rows_in_queue: int = 0
        result_events: Dict[int, asyncio.Event] = {}
        results: Dict[int, List] = {}
        results_ready: Dict[int, int] = {}

        async def calculate(batch_no_to_calculate):
            nonlocal results, batch_no, queue, n_rows_in_queue, results_ready
            if batch_no == batch_no_to_calculate:
                n_args = len(queue[0])
                n_results = len(queue)
                args = []
                for j in range(n_args):
                    args.append([element for call_args in queue for element in call_args[j]])
                queue = []
                n_rows_in_queue = 0
                batch_no += 1
                results[batch_no_to_calculate] = await func(*args)
                result_events[batch_no_to_calculate].set()
                results_ready[batch_no_to_calculate] = n_results

        @functools.wraps(func)
        async def batching_call(*args):
            my_batch_no = get_batch_no()
            start_index, stop_index = add_args_to_queue(args)

            await wait_for_calculation(my_batch_no)

            return get_results(start_index, stop_index, my_batch_no)

        def get_batch_no():
            if batch_no not in result_events:
                result_events[batch_no] = asyncio.Event()
            return batch_no

        def add_args_to_queue(args):
            """Add a new argument vector to the queue and return result indices"""
            nonlocal queue, n_rows_in_queue

            queue.append(args)
            offset = n_rows_in_queue
            n_rows_in_queue += len(args[0])
            return offset, n_rows_in_queue

        async def wait_for_calculation(batch_no_to_calculate):
            if n_rows_in_queue >= target_batch_size:
                await calculate(batch_no_to_calculate)
            else:
                try:
                    await asyncio.wait_for(result_events[batch_no].wait(), timeout=max_waiting_time)
                except asyncio.TimeoutError:
                    if batch_no == batch_no_to_calculate:
                        await calculate(batch_no_to_calculate)

        def get_results(start_index: int, stop_index: int, batch_no):
            nonlocal results_ready, result_events, results

            results_to_return = results[batch_no][start_index:stop_index]
            results_ready[batch_no] -= 1
            if results_ready[batch_no] == 0:
                del result_events[batch_no]
                del results[batch_no]
                del results_ready[batch_no]
            return results_to_return

        return batching_call

    return decorator
