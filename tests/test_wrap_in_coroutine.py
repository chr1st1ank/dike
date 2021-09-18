"""Tests for the dike.wrap_in_coroutine decorator"""
# pylint: disable=missing-function-docstring
import asyncio

from dike import wrap_in_coroutine


def test_wrap_function():
    """Wrap a function without arguments"""

    @wrap_in_coroutine
    def f():
        return "X"

    assert asyncio.run(f()) == "X"


def test_wrap_function_args():
    """Wrap a function with positional arguments"""

    @wrap_in_coroutine
    def f(*args):
        return args

    assert asyncio.run(f("A", 2)) == ("A", 2)


def test_wrap_function_kargs():
    """Wrap a function with keyword arguments"""

    @wrap_in_coroutine
    def f(**kwargs):
        return kwargs

    assert asyncio.run(f(a="A", b=2)) == dict(a="A", b=2)


def test_wrap_coroutine():
    """Wrap a coroutine without arguments"""

    @wrap_in_coroutine
    async def f():
        return "X"

    assert asyncio.run(f()) == "X"


def test_wrap_coroutine_args():
    """Wrap a coroutine with positional arguments"""

    @wrap_in_coroutine
    async def f(*args):
        return args

    assert asyncio.run(f("A", 2)) == ("A", 2)


def test_wrap_coroutine_kargs():
    """Wrap a coroutine with keyword arguments"""

    @wrap_in_coroutine
    async def f(**kwargs):
        return kwargs

    assert asyncio.run(f(a="A", b=2)) == dict(a="A", b=2)
