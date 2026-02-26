"""Push-based event stream with operator chaining.

Minimal reactive stream: emit values, subscribe to them, and compose
with debounce/map/filter operators. Each operator returns a new stream
(immutable chain). dispose() tears down the entire chain.
"""

from __future__ import annotations

import threading
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")

Disposer = Callable[[], None]


class EventStream(Generic[T]):
    """Push-based event stream with operator chaining."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[T], None]] = []
        self._children: list[EventStream] = []  # downstream streams for dispose
        self._disposed = False
        self._parent_disposer: Disposer | None = None

    def emit(self, value: T) -> None:
        """Push a value to all subscribers."""
        if self._disposed:
            return
        for cb in self._subscribers:
            cb(value)

    def subscribe(self, callback: Callable[[T], None]) -> Disposer:
        """Register a callback. Returns a function that removes it."""
        self._subscribers.append(callback)

        def _unsubscribe() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass  # already removed

        return _unsubscribe

    def debounce(self, seconds: float) -> EventStream[T]:
        """Coalesce rapid events — emit after quiet period.

        Uses threading.Timer (daemon=True). Each new event cancels the
        previous timer, so only the last event in a burst fires.
        """
        child: EventStream[T] = EventStream()
        child._parent_disposer = self._track_child(child)
        timer_lock = threading.Lock()
        timer_ref: list[threading.Timer | None] = [None]

        def _on_event(value: T) -> None:
            with timer_lock:
                if timer_ref[0] is not None:
                    timer_ref[0].cancel()
                t = threading.Timer(seconds, child.emit, args=[value])
                t.daemon = True
                timer_ref[0] = t
                t.start()

        self.subscribe(_on_event)
        return child

    def map(self, fn: Callable[[T], U]) -> EventStream[U]:
        """Transform events through fn."""
        child: EventStream[U] = EventStream()
        child._parent_disposer = self._track_child(child)
        self.subscribe(lambda v: child.emit(fn(v)))
        return child

    def filter(self, fn: Callable[[T], bool]) -> EventStream[T]:
        """Only pass events where fn returns True."""
        child: EventStream[T] = EventStream()
        child._parent_disposer = self._track_child(child)
        self.subscribe(lambda v: child.emit(v) if fn(v) else None)
        return child

    def dispose(self) -> None:
        """Tear down this stream and all downstream children."""
        self._disposed = True
        self._subscribers.clear()
        for child in self._children:
            child.dispose()
        self._children.clear()
        if self._parent_disposer is not None:
            self._parent_disposer()
            self._parent_disposer = None

    def _track_child(self, child: EventStream) -> Disposer:
        """Register child for dispose propagation. Returns a disposer that removes it."""
        self._children.append(child)

        def _remove() -> None:
            try:
                self._children.remove(child)
            except ValueError:
                pass

        return _remove
