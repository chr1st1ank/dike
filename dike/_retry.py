"""Implementation of the @dike.retry decorator"""
import asyncio
import datetime
import functools
import inspect
import logging
from typing import Awaitable, Callable, Tuple, Type, Union

logger = logging.getLogger("dike")


def retry(
    *,
    attempts: int = None,
    exception_types: Union[Type[BaseException], Tuple[Type[BaseException]]] = Exception,
    delay: datetime.timedelta = None,
    backoff: int = 1,
    log_exception_info: bool = True,
) -> Callable[[Callable[..., Awaitable]], Callable[..., Awaitable]]:
    """Decorator to limit the number of concurrent calls to a coroutine function. Not thread-safe.

    Args:
        attempts: The maximum number of tries before re-raising the last exception. Per default
            there is no limit.
        exception_types: The exception types which allow a retry. In case of other exceptions
            there is no retry.
        delay: Delay between attempts. Per default there is no delay.
        backoff: Multiplier applied to the delay between attempts. Per default this is `1`, so that
            the delay is constant and does not grow. E.g. use `2` to double the delay with each
            attempt.
        log_exception_info: Wether to include the exception stacktrace when logging any failed
            attempts. Default: True

    Returns:
        The given coroutine function with added exception handling and retry logic.

    Raises:
        ValueError: For invalid configuration arguments.

    Examples:
        >>> import asyncio
        >>> import httpx
        >>> import datetime
        >>> import dike
        ...
        >>> @dike.retry(attempts=2, delay=datetime.timedelta(milliseconds=10))
        ... async def web_request():
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get("https://httpstat.us/400")
        ...         if response.status_code != httpx.codes.OK:
        ...             raise RuntimeError("Request failed!")
        ...     return response
        ...
        ...
        >>> async def main():
        ...     response = await web_request()
        ...     print(response)
        ...
        ...
        >>> asyncio.run(main())
        ... # Log messages from two attempts:
        ... # WARNING:dike:Caught exception RuntimeError('Request failed!'). Retrying in 0.01s ...
        ... # Then:
        Traceback (most recent call last):
            ...
        RuntimeError: Request failed!
    """
    if attempts and not attempts >= 0:
        raise ValueError("Error when wrapping f(). max_attempts must be >= 0!")

    def decorator(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
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
                    logger.warning(
                        f"Caught exception {repr(e)}. Retrying in {next_delay:.3g}s ...",
                        exc_info=log_exception_info,
                    )
                    await asyncio.sleep(next_delay)
                    next_delay *= backoff

        return guarded_call

    return decorator
