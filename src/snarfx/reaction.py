"""Reactions — side effects triggered by observable state changes.

Unlike Computed (which is lazy and only evaluates on read), a Reaction
eagerly re-runs its side effect whenever its tracked dependencies change.

Two flavors:
- autorun(fn): runs fn immediately, re-runs when any observable it read changes.
- reaction(data_fn, effect_fn): tracks data_fn, calls effect_fn with the new value
  only when data_fn's result changes.

All state lives in _anchor — instances are thin handles holding an _id.
"""

from __future__ import annotations

from typing import TypeVar, Callable
from snarfx._tracking import current_derivation
from snarfx import _anchor

T = TypeVar("T")


class Reaction:
    """A reactive side effect that re-runs when its dependencies change.

    Reactions run eagerly (unlike Computed which is lazy).
    """

    __slots__ = ("_id",)

    def __init__(self, fn: Callable[[], None]) -> None:
        self._id = _anchor.new_id()
        _anchor.derivation_fns[self._id] = fn
        _anchor.dependencies[self._id] = set()
        _anchor.disposed[self._id] = False

    @property
    def _fn(self) -> Callable[[], None]:
        return _anchor.derivation_fns[self._id]

    @property
    def _dependencies(self) -> set:
        return _anchor.dependencies[self._id]

    @_dependencies.setter
    def _dependencies(self, value: set) -> None:
        _anchor.dependencies[self._id] = value

    def _run(self) -> None:
        """Re-evaluate the reaction function, re-tracking dependencies."""
        if _anchor.disposed[self._id]:
            return

        for dep in _anchor.dependencies[self._id]:
            dep._remove_observer(self)
        _anchor.dependencies[self._id].clear()

        token = current_derivation.set(self)
        try:
            self._fn()
        finally:
            current_derivation.reset(token)

    def dispose(self) -> None:
        """Stop this reaction. Disconnects from all dependencies."""
        _anchor.disposed[self._id] = True
        for dep in _anchor.dependencies[self._id]:
            dep._remove_observer(self)
        _anchor.dependencies[self._id].clear()

    def __repr__(self) -> str:
        state = "disposed" if _anchor.disposed[self._id] else "active"
        return f"Reaction({self._fn.__name__}, {state})"


class _DataReaction:
    """Internal: reaction(data_fn, effect_fn) implementation.

    Tracks data_fn's dependencies. When they change, re-runs data_fn.
    If the result differs from last time, calls effect_fn with the new value.
    """

    __slots__ = ("_id", "_effect_fn", "_last_value", "_initialized")

    def __init__(self, data_fn: Callable, effect_fn: Callable) -> None:
        self._id = _anchor.new_id()
        _anchor.derivation_fns[self._id] = data_fn
        _anchor.dependencies[self._id] = set()
        _anchor.disposed[self._id] = False
        self._effect_fn = effect_fn
        self._last_value = None
        self._initialized = False

    @property
    def _data_fn(self) -> Callable:
        return _anchor.derivation_fns[self._id]

    @property
    def _dependencies(self) -> set:
        return _anchor.dependencies[self._id]

    @_dependencies.setter
    def _dependencies(self, value: set) -> None:
        _anchor.dependencies[self._id] = value

    def _run(self) -> None:
        if _anchor.disposed[self._id]:
            return

        for dep in _anchor.dependencies[self._id]:
            dep._remove_observer(self)
        _anchor.dependencies[self._id].clear()

        token = current_derivation.set(self)
        try:
            new_value = self._data_fn()
        finally:
            current_derivation.reset(token)

        if not self._initialized or new_value != self._last_value:
            self._last_value = new_value
            self._initialized = True
            self._effect_fn(new_value)

    def dispose(self) -> None:
        _anchor.disposed[self._id] = True
        for dep in _anchor.dependencies[self._id]:
            dep._remove_observer(self)
        _anchor.dependencies[self._id].clear()

    def __repr__(self) -> str:
        state = "disposed" if _anchor.disposed[self._id] else "active"
        return f"_DataReaction({self._data_fn.__name__}, {state})"


def autorun(fn: Callable[[], None]) -> Reaction:
    """Run fn immediately, then re-run whenever any observable it reads changes.

    Returns the Reaction (call .dispose() to stop).

    Usage:
        counter = Observable(0)
        log = []

        dispose = autorun(lambda: log.append(counter.get()))
        # log == [0] — ran immediately

        counter.set(1)
        # log == [0, 1] — re-ran because counter changed

        dispose.dispose()
        counter.set(2)
        # log == [0, 1] — stopped
    """
    r = Reaction(fn)
    r._run()  # Initial run to establish dependencies
    return r


def reaction(
    data_fn: Callable[[], T],
    effect_fn: Callable[[T], None],
    *,
    fire_immediately: bool = False,
) -> _DataReaction:
    """Track data_fn's observables; call effect_fn when the result changes.

    Unlike autorun, effect_fn only fires when data_fn's *return value* changes,
    not on every dependency notification.

    Returns the reaction (call .dispose() to stop).

    Usage:
        first = Observable("Alice")
        last = Observable("Smith")

        effects = []
        r = reaction(
            lambda: f"{first.get()} {last.get()}",
            lambda name: effects.append(name),
        )
        # effects == [] — data_fn ran to establish deps, but effect doesn't fire yet

        first.set("Bob")
        # effects == ["Bob Smith"]

        last.set("Jones")
        # effects == ["Bob Smith", "Bob Jones"]

        r.dispose()
    """
    r = _DataReaction(data_fn, effect_fn)
    if fire_immediately:
        r._run()
    else:
        # Run data_fn to establish deps, but suppress the initial effect
        token = current_derivation.set(r)
        try:
            r._last_value = data_fn()
            r._initialized = True
        finally:
            current_derivation.reset(token)
    return r
