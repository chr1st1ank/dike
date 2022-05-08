# dike

**Python asyncio tools for web service resilience**

* Documentation: <https://chr1st1ank.github.io/dike/>

[<img src="https://img.shields.io/pypi/v/dike.svg" alt="Release Status">](https://pypi.python.org/pypi/dike)
[![GitHub license](https://img.shields.io/github/license/chr1st1ank/dike)](https://github.com/chr1st1ank/dike/blob/main/LICENSE)
[<img src="https://github.com/chr1st1ank/dike/actions/workflows/test.yml/badge.svg?branch=main" alt="CI Status">](https://github.com/chr1st1ank/dike/actions)
[![codecov](https://codecov.io/gh/chr1st1ank/dike/branch/main/graph/badge.svg?token=4oBkRHXbfa)](https://codecov.io/gh/chr1st1ank/dike)


## Features

### Retry decorator for asynchronous functions
A very common task especially for network calls is an automatic retry with proper exception
logging. There are good implementations like the [retry](https://pypi.org/project/retry/)
package for classic functions. But dike provides a similar implementation for coroutine functions.
This is available with the `@retry` decorator.

Simplified example:
```python
import asyncio
import datetime
import logging
import sys

import dike


@dike.retry(attempts=2, delay=datetime.timedelta(milliseconds=10), exception_types=RuntimeError)
async def web_request():
    raise RuntimeError("Request failed!")


async def main():
    response = await web_request()
    print(response)

logging.basicConfig(stream=sys.stdout)
asyncio.run(main())
```

The output shows first a warning log message including the exception info (that's configurable).
This is especially useful if you use structured logging.
```
# Log for first attempt:
WARNING:dike:Caught exception RuntimeError('Request failed!'). Retrying in 0.01s ...
Traceback (most recent call last):
...
RuntimeError: Request failed!
```

Then, the for the final failure the exception is propagated to the function caller:
```
Traceback (most recent call last):
  ...
RuntimeError: Request failed!

Process finished with exit code 1
```


### Concurrency limiting for asynchronous functions
The `@limit_jobs` decorator allows to limit the number of concurrent excecutions of a coroutine
function. This can be useful for limiting queueing times or for limiting the load put
onto backend services.

Example with an external web request using the [httpx](https://github.com/encode/httpx) library:

```python
import asyncio
import dike
import httpx


@dike.limit_jobs(limit=2)
async def web_request():
    """Sends a slow web request"""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpstat.us/200?sleep=100")
    return response


async def main():
    # Send three requests at the same time
    call1 = web_request()
    call2 = web_request()
    call3 = web_request()
    responses = await asyncio.gather(call1, call2, call3, return_exceptions=True)
    # Print the responses
    for r in responses:
        if isinstance(r, dike.TooManyCalls):
            print("too many calls")
        else:
            print(r)


asyncio.run(main())
```

The output shows that the first two requests succeed. The third one hits the concurrency limit and a TooManyCalls exception is returned:
```
<Response [200 OK]>
<Response [200 OK]>
too many calls
```

### Mini-batching for asynchronous function calls
The `@batch` decorator groups function calls into batches and only calls the wrapped function
with the aggregated input.

This is useful if the function scales well with the size of the input arguments but you're
getting the input data in smaller bits, e.g. as individual HTTP requests.

The arguments can be batched together as a Python list or optionally also as numpy array.

Example:

```python
import asyncio
import dike


@dike.batch(target_batch_size=3, max_waiting_time=10)
async def add_args(arg1, arg2):
    """Elementwise sum of the values in arg1 and arg2"""
    print(f"arg1: {arg1}")
    print(f"arg2: {arg2}")
    return [a1 + a2 for a1, a2 in zip(arg1, arg2)]


async def main():
    result = await asyncio.gather(
        add_args([0], [1]),
        add_args([1], [1]),
        add_args([2, 3], [1, 1]),
    )

    print(f"Result: {result}")


asyncio.run(main())
```

Output:
```
arg1: [0, 1, 2, 3]
arg2: [1, 1, 1, 1]
Result: [[1], [2], [3, 4]]
```

## Installation
Simply install from pypi. The library is pure Python without any dependencies other than the
standard library.
```
pip install dike
```
