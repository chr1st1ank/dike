"""Decorator library"""
import asyncio
import functools
import inspect
from typing import Callable, Dict, List, Tuple, Union

try:
    import numpy as np
except ImportError:
    np = None


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
    """Error raised by @limit_jobs when a call exceeds the preset limit"""


def limit_jobs(*, limit: int):
    """Decorator to limit the number of concurrent calls to a coroutine function. Not thread-safe.

    Args:
        limit: The maximum number of ongoing calls allowed at any time

    Returns:
        The given coroutine function with added concurrency protection

    Raises:
        TooManyCalls: The decorated function raises a dike.ToomanyCalls exception
            if it is called while already running `limit` times concurrently.
        ValueError: If the decorator is applied to something else than an async def function

    Note:
        The decorator is not thread-safe, but only allows for concurrent access by async functions.
        The wrapped function may use multithreading, but only one thread at a time may call the
        function in order to avoid race conditions.

    Examples:
        >>> import asyncio
        >>> import httpx
        >>> import dike
        ...
        ...
        >>> @dike.limit_jobs(limit=2)
        ... async def web_request():
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get("https://httpstat.us/200?sleep=100")
        ...     return response
        ...
        ...
        >>> async def main():
        ...     responses = await asyncio.gather(
        ...         web_request(), web_request(), web_request(), return_exceptions=True
        ...     )
        ...     for r in responses:
        ...         if isinstance(r, dike.TooManyCalls):
        ...             print("too many calls")
        ...         else:
        ...             print(r)
        ...
        ...
        >>> asyncio.run(main())
        <Response [200 OK]>
        <Response [200 OK]>
        too many calls
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
                raise TooManyCalls(f"Too many calls to {str(func)}! limit={limit}")
            try:
                counter -= 1
                return await func(*args, **kwargs)
            finally:
                counter += 1

        return limited_call

    return decorator


# Deactivate mccabe's complexity warnings which doesn't like closures
# flake8: noqa: C901
def batch(
    *,
    target_batch_size: int,
    max_waiting_time: float,
    max_processing_time: float = 10.0,
    argument_type: str = "list",
):
    """@batch is a decorator to cumulate function calls and process them in batches.
        Not thread-safe.

    The function to wrap must have arguments of type list or numpy.array which can be aggregated.
    It must return just a single value of the same type. The type has to be specified with the
    `argument_type` parameter of the decorator.

    Args:
        target_batch_size: As soon as the collected function arguments reach target_batch_size,
            the wrapped function is called and the results are returned. Note that the function
            may also be called with longer arguments than target_batch_size.
        max_waiting_time: Maximum waiting time in seconds before calling the underlying function
            although the target_batch_size hasn't been reached.
        max_processing_time: Maximum time in seconds for the processing itself (without waiting)
            before an asyncio.TimeoutError is raised. Note: It is strongly advised to set a
            reasonably strict timeout here in order not to create starving tasks which never finish
            in case something is wrong with the backend call.
        argument_type: The type of function argument used for batching. One of "list" or "numpy".
            Per default "list" is used, i.e. it is assumed that the input arguments to the
            wrapped functions are lists which can be concatenated. If set to "numpy" the arguments
            are assumed to be numpy arrays which can be concatenated by numpy.concatenate()
            along axis 0.

    Raises:
        ValueError: If the arguments target_batch_size or max_waiting time are not >= 0 or if the
            argument_type is invalid.
        ValueError: When calling the function with incorrect or inconsistent arguments.
        asyncio.TimeoutError: Is raised when calling the wrapped function takes longer than
            max_processing_time

    Returns:
        A coroutine function which executed the wrapped function with batches of input arguments.

    The wrapped function is called with concatenated arguments of multiple calls.

    Notes:
    - The decorator is not thread-safe, but only allows for concurrent access by async functions.
        The wrapped function may use multithreading, but only one thread at a time may call the
        function in order to avoid race conditions.
    - The return value of the wrapped function must be a single iterable.
    - All calls to the underlying function need to have the same number of positional arguments and
        the same keyword arguments. It also isn't possible to mix the two ways to pass an argument.
        The same argument always has to be passed either as keyword argument or as positional
        argument.

    Example:
        >>> import asyncio
        >>> import dike
        ...
        ...
        >>> @dike.batch(target_batch_size=3, max_waiting_time=10)
        ... async def f(arg1, arg2):
        ...     print(f"arg1: {arg1}")
        ...     print(f"arg2: {arg2}")
        ...     return [10, 11, 12]
        ...
        ...
        >>> async def main():
        ...     result = await asyncio.gather(
        ...         f([0], ["a"]),
        ...         f([1], ["b"]),
        ...         f([2], ["c"]),
        ...     )
        ...
        ...     print(f"Result: {result}")
        ...
        ...
        >>> asyncio.run(main())
        arg1: [0, 1, 2]
        arg2: ['a', 'b', 'c']
        Result: [[10], [11], [12]]
    """
    if not target_batch_size > 0:
        raise ValueError(f"target_batch_size must be > 0, but got {target_batch_size}")
    if not max_waiting_time > 0:
        raise ValueError(f"max_waiting_time must be > 0, but got {max_waiting_time}")
    if argument_type not in {"list", "numpy"}:
        raise ValueError(
            f'Invalid argument_type "{argument_type}". Must be one of "string", "numpy"'
        )
    if argument_type == "numpy" and np is None:
        raise ValueError('Unable to use "numpy" as argument_type because numpy is not available')

    def decorator(func):
        batch_no: int = 0
        queue: List[Tuple[List, Dict]] = []
        n_rows_in_queue: int = 0
        result_events: Dict[int, asyncio.Event] = {}
        results: Dict[int, Union[Exception, List]] = {}
        results_ready: Dict[int, int] = {}

        @functools.wraps(func)
        async def batching_call(*args, **kwargs):
            my_batch_no = get_batch_no()
            start_index, stop_index = add_args_to_queue(args, kwargs)

            await wait_for_calculation(my_batch_no)

            return get_results(start_index, stop_index, my_batch_no)

        def get_batch_no():
            if batch_no not in result_events:
                result_events[batch_no] = asyncio.Event()
            return batch_no

        def add_args_to_queue(args, kwargs):
            """Add a new argument vector to the queue and return result indices"""
            nonlocal queue, n_rows_in_queue

            if queue and (len(args) != len(queue[0][0]) or kwargs.keys() != queue[0][1].keys()):
                raise ValueError("Inconsistent use of positional and keyword arguments")
            n_rows_call = 0
            if args:
                n_rows_call = len(args[0])
            elif kwargs:
                for v in kwargs.values():
                    n_rows_call = len(v)
                    break  # We only need one arbitrary keyword argument
            if n_rows_call == 0:
                raise ValueError("Function called with empty collections as arguments")
            queue.append((args, kwargs))
            offset = n_rows_in_queue
            n_rows_in_queue += n_rows_call
            return offset, n_rows_in_queue

        async def wait_for_calculation(batch_no_to_calculate):
            if n_rows_in_queue >= target_batch_size:
                await calculate(batch_no_to_calculate)
            else:
                try:
                    await asyncio.wait_for(
                        result_events[batch_no_to_calculate].wait(), timeout=max_waiting_time
                    )
                except asyncio.TimeoutError:
                    if batch_no == batch_no_to_calculate:
                        await calculate(batch_no_to_calculate)
                    else:
                        await asyncio.wait_for(
                            result_events[batch_no_to_calculate].wait(), timeout=max_processing_time
                        )

        async def calculate(batch_no_to_calculate):
            nonlocal results, queue, results_ready
            if batch_no == batch_no_to_calculate:
                n_results = len(queue)
                args, kwargs = pop_args_from_queue()
                try:
                    results[batch_no_to_calculate] = await func(*args, **kwargs)
                except Exception as e:  # pylint: disable=broad-except
                    results[batch_no_to_calculate] = e
                results_ready[batch_no_to_calculate] = n_results
                result_events[batch_no_to_calculate].set()

        def pop_args_from_queue():
            nonlocal batch_no, queue, n_rows_in_queue

            n_args = len(queue[0][0])
            args = []
            for j in range(n_args):
                if argument_type == "list":
                    args.append([element for call_args, _ in queue for element in call_args[j]])
                elif argument_type == "numpy":
                    args.append(np.concatenate([call_args[j] for call_args, _ in queue]))
            kwargs = {}
            for k in queue[0][1].keys():
                if argument_type == "list":
                    kwargs[k] = [element for _, call_kwargs in queue for element in call_kwargs[k]]
                elif argument_type == "numpy":
                    kwargs[k] = np.concatenate([call_kwargs[k] for _, call_kwargs in queue])

            queue = []
            n_rows_in_queue = 0
            batch_no += 1
            return args, kwargs

        def get_results(start_index: int, stop_index: int, batch_no):
            nonlocal results

            if isinstance(results[batch_no], Exception):
                exc = results[batch_no]
                remove_result(batch_no)
                raise exc
            results_to_return = results[batch_no][start_index:stop_index]
            remove_result(batch_no)
            return results_to_return

        def remove_result(batch_no):
            nonlocal results_ready, result_events, results

            results_ready[batch_no] -= 1
            if results_ready[batch_no] == 0:
                del result_events[batch_no]
                del results[batch_no]
                del results_ready[batch_no]

        return batching_call

    return decorator
