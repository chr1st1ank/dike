# aiodike - Python asyncio tools for web service resilience

[<img src="https://img.shields.io/pypi/v/aiodike.svg" alt="Release Status">](https://pypi.python.org/pypi/aiodike)
[<img src="https://github.com/chr1st1ank/aiodike/actions/workflows/test.yml/badge.svg?branch=main" alt="CI Status">](https://github.com/chr1st1ank/aiodike/actions)
[![codecov](https://codecov.io/gh/chr1st1ank/aiodike/branch/main/graph/badge.svg?token=4oBkRHXbfa)](https://codecov.io/gh/chr1st1ank/aiodike)


* Documentation: <https://chr1st1ank.github.io/aiodike/>
* License: Apache-2.0
* Status: Initial development

## Features

### Concurrency limiting for asynchronous functions
The `@limit_jobs` decorator allows to limit the number of concurrent excecutions of a coroutine 
function.

### Mini-batching for asynchronous function calls
The `@batch` decorator groups function calls into batches and only calls the wrapped function 
once on the collected input.

## Installation
```
pip install aiodike
```
