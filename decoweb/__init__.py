import asyncio
import concurrent
import functools
import inspect
from dataclasses import dataclass
from typing import Callable, List, Sequence, Iterable, Awaitable, Union


def wrap_in_coroutine(func: Callable) -> Callable:
    """Decorator to wrap a function into a coroutine.

    If `func` is already a coroutine it is returned as-is.

    Args:
        func: A callable object (function or coroutine)

    Returns:
        A coroutine which executes `func`.
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
    """Decorator to limit the number of concurrent calls to a coroutine.

    Args:
        limit: The maximum number of ongoing calls allowed at any time

    Returns:
        The given coroutine with added concurrency protection

    Raises:
        TooManyCalls: The decorated function raises a decoweb.ToomanyCalls exception
            if it is called more than `limit` times concurrently.
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
                raise TooManyCalls()
            try:
                counter -= 1
                return await func(*args, **kwargs)
            finally:
                counter += 1

        return limited_call

    return decorator
