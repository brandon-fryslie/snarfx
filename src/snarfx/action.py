"""Actions and transactions — batched state mutations.

Wrapping mutations in an @action or `with transaction()` defers all
reaction/computed invalidation until the outermost scope exits.
This prevents glitchy intermediate states where some dependents have
updated but others haven't yet.
"""

from __future__ import annotations

import functools
from typing import TypeVar, Callable, ParamSpec
from contextlib import contextmanager
from snarfx._tracking import begin_batch, end_batch

P = ParamSpec("P")
R = TypeVar("R")


def action(fn: Callable[P, R]) -> Callable[P, R]:
    """Decorator: batch all observable mutations inside fn.

    Reactions only fire after fn returns, not during.

    Usage:
        counter_a = Observable(0)
        counter_b = Observable(0)

        @action
        def swap():
            a, b = counter_a.get(), counter_b.get()
            counter_a.set(b)
            counter_b.set(a)
            # reactions see both changes at once, not one at a time
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        begin_batch()
        try:
            return fn(*args, **kwargs)
        finally:
            end_batch()

    return wrapper


@contextmanager
def transaction():
    """Context manager for batching mutations.

    Usage:
        with transaction():
            counter_a.set(1)
            counter_b.set(2)
            # reactions fire here, after both are set
    """
    begin_batch()
    try:
        yield
    finally:
        end_batch()
