import asyncio
import datetime

import pytest

import dike


@pytest.mark.parametrize("attempts", [None, 1, 2, 3, 2.5, float("inf")])
def test_no_exception(attempts):
    """No exception."""

    @dike.retry(attempts=attempts)
    async def f():
        return "x"

    assert asyncio.run(f()) == "x"


@pytest.mark.parametrize("exception_types", [ValueError, (Exception,)])
@pytest.mark.parametrize("attempts", [None, 2, 3, 2.5, float("inf")])
def test_exception_with_retry(attempts, exception_types):
    """Exception and finally success."""
    i = 1

    @dike.retry(attempts=attempts, exception_types=exception_types)
    async def f():
        nonlocal i
        if i > 0:
            i -= 1
            raise ValueError()
        return "x"

    assert asyncio.run(f()) == "x"


@pytest.mark.parametrize("attempts", [1, 2])
def test_exception_with_retry_failed(attempts, caplog):
    """Running over the maximum number of attempts."""
    i = 2

    @dike.retry(attempts=attempts, exception_types=ValueError)
    async def f():
        nonlocal i
        if i > 0:
            i -= 1
            raise ValueError("failure")
        return "x"

    with pytest.raises(ValueError):
        print(asyncio.run(f()))
    assert i == 2 - attempts
    assert caplog.messages == [
        "Caught exception ValueError('failure'). Retrying in 0s ..." for _ in range(attempts - 1)
    ]


@pytest.mark.parametrize(
    "delay",
    [
        None,
        datetime.timedelta(seconds=1),
        datetime.timedelta(seconds=2),
        datetime.timedelta(milliseconds=10),
    ],
)
@pytest.mark.parametrize("backoff", [1, 2.5])
def test_sleep_time(delay, backoff, monkeypatch):
    """Running over the maximum number of attempts."""
    n_calls = 0

    async def sleep(seconds):
        if not delay:
            assert seconds == 0
        else:
            assert seconds == delay.total_seconds() * backoff ** (n_calls - 1)

    monkeypatch.setattr(asyncio, "sleep", sleep)

    @dike.retry(attempts=3, exception_types=ValueError, delay=delay, backoff=backoff)
    async def f():
        nonlocal n_calls
        n_calls += 1
        raise ValueError()

    with pytest.raises(ValueError):
        asyncio.run(f())
    assert n_calls == 3
