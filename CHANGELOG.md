# History

## Unreleased

## 0.2.0 (2021-07-15)
Added:
* Propagation of function exceptions to all callers for the @batch decorator
* A dockerized example service using minibatching and load shedding

Fixed:
* Occasional Python 3.8 f-strings were replaced by a Python 3.7 compatible implementation
* A race condition was fixed that occurred in case of multiple concurrent calls running into the
  max_waiting_time at the same moment

## 0.1.0 (2021-07-13)
Added:
* @batch decorator for minibatching of coroutine calls.
* @limit_jobs decorator to limit the number of concurrent calls to a coroutine function.
