"""Implementation of the @dike.retry decorator"""
import asyncio
import datetime
import functools
import inspect
import logging
from typing import Any, Callable, Coroutine, Union, Type, Tuple

logger = logging.getLogger("dike")

def retry(
    *,
    attempts: int = None,
    exception_types: Union[Type[BaseException], Tuple[Type[BaseException]]]=Exception,
    delay: datetime.timedelta = None,
    backoff: int = 1,
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to limit the number of concurrent calls to a coroutine function. Not thread-safe.

    Args:
        attempts: The maximum number of tries before re-raising the last exception. Per default
            there is no limit.
        exception_types: The exception types which allow a retry. In case of other exceptions
            there is no retry.
        delay: Delay between attempts. Per default there is no delay.
        backoff: Multiplier applied to the delay between attempts. Per default this is `1`, so that
            the delay is constant and does not grow.


    Returns:
        The given coroutine function with added exception handling and retry logic.

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
    if attempts and not attempts >= 0:
        raise ValueError("Error when wrapping f(). max_attempts must be >= 0!")
    # if not (isinstance(exception_types, tuple) or issubclass(exception_types, BaseException)):
    #     raise ValueError(
    #         "Error when wrapping f(). exception_types must be an "
    #         "exception type or a tuple of exception types!"
    #     )

    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Error when wrapping {str(func)}. Only coroutines can be wrapped!")

        @functools.wraps(func)
        async def guarded_call(*args, **kwargs):
            counter = -1 if attempts is None else attempts
            next_delay = 0 if delay is None else delay.total_seconds()

            while counter:
                try:
                    x = await func(*args, **kwargs)
                    return x
                except exception_types as e:
                    counter -= 1
                    if not counter:
                        raise
                    logger.warning(f"Caught exception {e}. Retrying in {next_delay:.3f}s ...")
                    await asyncio.sleep(next_delay)
                    next_delay *= backoff

        return guarded_call

    return decorator
