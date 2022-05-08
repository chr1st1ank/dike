# Usage

To use dike in a project

```
    import dike
```


## Managing CPU bound work in a process pool

```python
import asyncio
import concurrent

import dike

from my_project import cpu_bound_function

pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)


@dike.limit_jobs(limit=4)
def calculate_in_pool(args):
    """Run calculations of cpu_bound_function() in a process pool with limited queue"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, cpu_bound_function, *args)
```


## Minibatching the inputs of a machine learning model
