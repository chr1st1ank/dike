import asyncio
import concurrent
import functools
import inspect
from dataclasses import dataclass
from typing import Callable, List, Sequence, Iterable


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


def limit_jobs(*, limit, error_callback: Callable=tuple):
    """

    Args:
        limit:
        error_callback:

    Returns:

    """
    semaphore = asyncio.Semaphore(limit)
    on_error = wrap_in_coroutine(error_callback)

    def decorator(func):
        @functools.wraps(func)
        async def limited_call(*args, **kwargs):
            if semaphore.locked():
                return await on_error(*args, **kwargs)
            async with semaphore:
                return await func(*args, **kwargs)

        return limited_call

    return decorator
