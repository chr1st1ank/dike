# History

## Unreleased
Fixed:
* Occasional Python 3.8 f-strings were replaced by a Python 3.7 compatible implementation

## 0.1.0 (2021-07-13)
  
Added:
* @batch decorator for minibatching of coroutine calls.
* @limit_jobs decorator to limit the number of concurrent calls to a coroutine function.
