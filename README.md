# dike - Python asyncio tools for web service resilience

[<img src="https://img.shields.io/pypi/v/dike.svg" alt="Release Status">](https://pypi.python.org/pypi/dike)
[<img src="https://github.com/chr1st1ank/dike/actions/workflows/test.yml/badge.svg?branch=main" alt="CI Status">](https://github.com/chr1st1ank/dike/actions)
[![codecov](https://codecov.io/gh/chr1st1ank/dike/branch/main/graph/badge.svg?token=4oBkRHXbfa)](https://codecov.io/gh/chr1st1ank/dike)


* Documentation: <https://chr1st1ank.github.io/dike/>
* License: Apache-2.0
* Status: Initial development

## Features

### Concurrency limiting for asynchronous functions
The `@limit_jobs` decorator allows to limit the number of concurrent excecutions of a coroutine 
function. This can be useful for limiting queueing times or for limiting the load put
onto backend services.

Example with an external web request using the [httpx](https://github.com/encode/httpx) library:

```python
import asyncio
import httpx
import dike


@dike.limit_jobs(limit=2)
async def web_request():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpstat.us/200?sleep=100")
    return response


async def main():
    responses = await asyncio.gather(
        web_request(), web_request(), web_request(), return_exceptions=True
    )
    for r in responses:
        if isinstance(r, dike.TooManyCalls):
            print("too many calls")
        else:
            print(r)


asyncio.run(main())
```

The output shows that the first two requests succeed. The third one hits the concurrency limit:
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

Example:

```python
import asyncio
import dike


@dike.batch(target_batch_size=3, max_waiting_time=10)
async def f(arg1, arg2):
    print(f"arg1: {arg1}")
    print(f"arg2: {arg2}")
    return [10, 11, 12]


async def main():
    result = await asyncio.gather(
        f([0], ["a"]),
        f([1], ["b"]),
        f([2], ["c"]),
    )

    print(f"Result: {result}")


asyncio.run(main())
```

Output:
```
arg1: [0, 1, 2]
arg2: ['a', 'b', 'c']
Result: [[10], [11], [12]]
```

## Installation
Simply install from pypi. The library is pure Python without any dependencies other than the
standard library.
```
pip install dike
```
