# History
Changelog in the style of [keepachangelog.com](https://keepachangelog.com/).

Types of changes:
* 'Added' for new features.
* 'Changed' for changes in existing functionality.
* 'Deprecated' for soon-to-be removed features.
* 'Removed' for now removed features.
* 'Fixed' for any bug fixes.
* 'Security' in case of vulnerabilities.

The project uses semantic versioning.

## [Unreleased]

## [1.0.1] - 2024-10-15
### Changed:
* Updates of dependencies and change of build tool to uv

## [1.0.0] - 2022-05-09
### Added:
* Package API declared stable.

## [0.4.0] - 2022-05-08
### Added:
* New @retry decorator for retries of coroutine calls.

## [0.3.1] - 2021-09-25
### Added:
* Doctests to ensure the examples in the documentation keep being correct

### Fixed:
* A potential memory leak in case was fixed. It could occur if one of the tasks waiting for the
  result of a function decorated with @batch was cancelled.

### Changed:
* Decorators are now implemented in submodules. The public interface is unchanged

## [0.3.0] - 2021-07-15
### Added:
* Support for numpy arrays in the @batch decorator

## [0.2.0] - 2021-07-15
### Added:
* Propagation of function exceptions to all callers for the @batch decorator
* A dockerized example service using minibatching and load shedding

### Fixed:
* Occasional Python 3.8 f-strings were replaced by a Python 3.7 compatible implementation
* A race condition was fixed that occurred in case of multiple concurrent calls running into the
  max_waiting_time at the same moment

## [0.1.0] - 2021-07-13
### Added:
* New @batch decorator for minibatching of coroutine calls.
* New @limit_jobs decorator to limit the number of concurrent calls to a coroutine function.
