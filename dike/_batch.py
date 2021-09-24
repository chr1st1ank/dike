"""Implementation of the @dike.batch decorator"""
import asyncio
import functools
from contextlib import contextmanager
from typing import Any, Callable, Coroutine, Dict, List, Tuple, Union

try:
    import numpy as np
except ImportError:
    np = None


# Deactivate mccabe's complexity warnings which doesn't like closures
# flake8: noqa: C901
def batch(
    *,
    target_batch_size: int,
    max_waiting_time: float,
    max_processing_time: float = 10.0,
    argument_type: str = "list",
) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
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
        next_free_batch: int = 0
        call_args_queue: List[Tuple[List, Dict]] = []
        n_rows_in_queue: int = 0
        result_ready_events: Dict[int, asyncio.Event] = {}
        results: Dict[int, Union[Exception, List]] = {}
        num_results_ready: Dict[int, int] = {}

        @functools.wraps(func)
        async def batching_call(*args, **kwargs):
            """This is the actual wrapper function which controls the process"""
            nonlocal results, num_results_ready, result_ready_events, call_args_queue, n_rows_in_queue

            with enqueue(args, kwargs) as (my_batch_no, start_index, stop_index):
                await wait_for_calculation(my_batch_no)
                return get_results(start_index, stop_index, my_batch_no)

        @contextmanager
        def enqueue(args, kwargs) -> (int, int, int):
            """Add call arguments to queue and get the batch number and result indices"""
            batch_no = next_free_batch
            if batch_no not in result_ready_events:
                result_ready_events[batch_no] = asyncio.Event()
            start_index, stop_index = add_args_to_queue(args, kwargs)
            try:
                yield batch_no, start_index, stop_index
            finally:
                remove_result(batch_no)

        def add_args_to_queue(args, kwargs):
            """Add a new argument vector to the queue and return result indices"""
            nonlocal call_args_queue, n_rows_in_queue

            if call_args_queue and (
                len(args) != len(call_args_queue[0][0])
                or kwargs.keys() != call_args_queue[0][1].keys()
            ):
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
            call_args_queue.append((args, kwargs))
            offset = n_rows_in_queue
            n_rows_in_queue += n_rows_call
            return offset, n_rows_in_queue

        async def wait_for_calculation(batch_no_to_calculate):
            """Pause until the result becomes available or trigger the calculation on timeout"""
            if n_rows_in_queue >= target_batch_size:
                await calculate(batch_no_to_calculate)
            else:
                try:
                    await asyncio.wait_for(
                        result_ready_events[batch_no_to_calculate].wait(), timeout=max_waiting_time
                    )
                except asyncio.TimeoutError:
                    if next_free_batch == batch_no_to_calculate:
                        await calculate(batch_no_to_calculate)
                    else:
                        await asyncio.wait_for(
                            result_ready_events[batch_no_to_calculate].wait(),
                            timeout=max_processing_time,
                        )

        async def calculate(batch_no_to_calculate):
            """Call the decorated coroutine with batched arguments"""
            nonlocal results, call_args_queue, num_results_ready
            if next_free_batch == batch_no_to_calculate:
                n_results = len(call_args_queue)
                args, kwargs = pop_args_from_queue()
                try:
                    results[batch_no_to_calculate] = await func(*args, **kwargs)
                except Exception as e:  # pylint: disable=broad-except
                    results[batch_no_to_calculate] = e
                num_results_ready[batch_no_to_calculate] = n_results
                result_ready_events[batch_no_to_calculate].set()

        def pop_args_from_queue():
            """Get all collected arguments from the queue as batch"""
            nonlocal next_free_batch, call_args_queue, n_rows_in_queue

            n_args = len(call_args_queue[0][0])
            args = []
            for j in range(n_args):
                if argument_type == "list":
                    args.append(
                        [element for call_args, _ in call_args_queue for element in call_args[j]]
                    )
                elif argument_type == "numpy":
                    args.append(np.concatenate([call_args[j] for call_args, _ in call_args_queue]))
            kwargs = {}
            for k in call_args_queue[0][1].keys():
                if argument_type == "list":
                    kwargs[k] = [
                        element for _, call_kwargs in call_args_queue for element in call_kwargs[k]
                    ]
                elif argument_type == "numpy":
                    kwargs[k] = np.concatenate(
                        [call_kwargs[k] for _, call_kwargs in call_args_queue]
                    )

            call_args_queue = []
            n_rows_in_queue = 0
            next_free_batch += 1
            return args, kwargs

        def get_results(start_index: int, stop_index: int, batch_no):
            """Pop the results for a certain index range from the output buffer"""
            nonlocal results

            if isinstance(results[batch_no], Exception):
                exc = results[batch_no]
                raise exc
            results_to_return = results[batch_no][start_index:stop_index]
            return results_to_return

        def remove_result(batch_no):
            """Reduce reference count to output buffer and eventually delete it"""
            nonlocal num_results_ready, result_ready_events, results

            if num_results_ready[batch_no] == 1:
                del result_ready_events[batch_no]
                del results[batch_no]
                del num_results_ready[batch_no]
            else:
                num_results_ready[batch_no] -= 1

        return batching_call

    return decorator
