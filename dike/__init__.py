"""Decorator library"""
import functools
import inspect
from typing import Callable

from ._batch import batch
from ._limit_jobs import TooManyCalls, limit_jobs


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


__all__ = ["batch", "limit_jobs", "TooManyCalls", "wrap_in_coroutine"]
