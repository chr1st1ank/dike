"""Implementation of the @dike.limit_jobs decorator"""
import functools
import inspect
from typing import Any, Callable, Coroutine


class TooManyCalls(Exception):
    """Error raised by @limit_jobs when a call exceeds the preset limit"""


def limit_jobs(*, limit: int) -> Callable[..., Coroutine[Any, Any, Any]]:
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
        The decorator is not thread-safe, but only allows for concurrent access by async
        functions. The wrapped function may use multithreading, but only one thread at a time
        may call the function in order to avoid race conditions.

    Examples:
        >>> import dike
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
        ...         if isinstance(r, dike._limit_jobs.TooManyCalls):
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
                raise TooManyCalls(
                    f"Too many calls to function {func.__name__}! limit={limit} exceeded"
                )
            try:
                counter -= 1
                return await func(*args, **kwargs)
            finally:
                counter += 1

        return limited_call

    return decorator
