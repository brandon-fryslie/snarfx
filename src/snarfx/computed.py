"""Computed values — derived state with automatic dependency tracking.

A Computed wraps a function. When evaluated, it tracks which observables
the function reads and caches the result. When any dependency changes,
the cached value is invalidated. On next read, it re-evaluates.

Computed values are lazy — they only recompute when read.

All state lives in _anchor — instances are thin handles holding an _id.
"""

from __future__ import annotations

from typing import TypeVar, Generic, Callable
from snarfx._tracking import current_derivation, schedule
from snarfx import _anchor

T = TypeVar("T")

_UNSET = object()


class Computed(Generic[T]):
    """A derived value that auto-tracks dependencies and caches the result."""

    __slots__ = ("_id",)

    def __init__(self, fn: Callable[[], T]) -> None:
        self._id = _anchor.new_id()
        _anchor.derivation_fns[self._id] = fn
        _anchor.cached_values[self._id] = _UNSET
        _anchor.dirty_flags[self._id] = True
        _anchor.dependencies[self._id] = set()
        _anchor.observers[self._id] = set()

    @property
    def _fn(self) -> Callable[[], T]:
        return _anchor.derivation_fns[self._id]

    @property
    def _dependencies(self) -> set:
        return _anchor.dependencies[self._id]

    @_dependencies.setter
    def _dependencies(self, value: set) -> None:
        _anchor.dependencies[self._id] = value

    def get(self) -> T:
        """Read the computed value. Recomputes if dirty."""
        derivation = current_derivation.get()
        if derivation is not None:
            _anchor.observers[self._id].add(derivation)
            derivation._dependencies.add(self)

        if _anchor.dirty_flags[self._id]:
            self._recompute()

        return _anchor.cached_values[self._id]

    def _recompute(self) -> None:
        """Re-evaluate the function, tracking dependencies."""
        for dep in _anchor.dependencies[self._id]:
            dep._remove_observer(self)
        _anchor.dependencies[self._id].clear()

        token = current_derivation.set(self)
        try:
            _anchor.cached_values[self._id] = self._fn()
        finally:
            current_derivation.reset(token)

        _anchor.dirty_flags[self._id] = False

    def _run(self) -> None:
        """Called by the scheduler when a dependency changed.

        For Computed, we mark dirty and propagate to our own observers.
        We don't recompute eagerly — that happens on next .get().
        """
        if not _anchor.dirty_flags[self._id]:
            _anchor.dirty_flags[self._id] = True
            for observer in list(_anchor.observers[self._id]):
                schedule(observer)

    def _remove_observer(self, observer) -> None:
        _anchor.observers[self._id].discard(observer)

    def dispose(self) -> None:
        """Disconnect from all dependencies. The computed becomes inert."""
        for dep in _anchor.dependencies[self._id]:
            dep._remove_observer(self)
        _anchor.dependencies[self._id].clear()
        _anchor.observers[self._id].clear()
        _anchor.dirty_flags[self._id] = True
        _anchor.cached_values[self._id] = _UNSET

    def __repr__(self) -> str:
        dirty = _anchor.dirty_flags[self._id]
        val = _anchor.cached_values[self._id]
        state = "dirty" if dirty else f"cached={val!r}"
        return f"Computed({self._fn.__name__}, {state})"


def computed(fn: Callable[[], T]) -> Computed[T]:
    """Decorator/factory to create a Computed from a function.

    Usage:
        counter = Observable(0)

        @computed
        def doubled():
            return counter.get() * 2

        doubled.get()  # 0
        counter.set(5)
        doubled.get()  # 10
    """
    return Computed(fn)
