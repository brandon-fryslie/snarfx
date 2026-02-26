"""Observable values — state that tracks its readers.

When an Observable is read inside a Computed or Reaction evaluation,
the dependency is automatically registered. When the Observable changes,
all dependents are scheduled for re-evaluation.

All state lives in _anchor — instances are thin handles holding an _id.

Thread safety: call set_scheduler() once from the main thread. After that,
any .set() from a background thread is auto-marshaled. Main-thread .set()
remains synchronous.
"""

from __future__ import annotations

import threading
from typing import TypeVar, Generic, Iterator, overload
from snarfx._tracking import current_derivation, schedule
from snarfx import _anchor

T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")

# ─── Auto-marshal ────────────────────────────────────────────────────────────
_scheduler = None
_scheduler_thread = None


def set_scheduler(scheduler) -> None:
    """Set the global thread scheduler for cross-thread Observable mutations.

    Call once from the main/UI thread:
        snarfx.set_scheduler(app.call_from_thread)

    After this, any Observable.set() from a background thread is automatically
    marshaled. Main-thread mutations remain synchronous.
    """
    global _scheduler, _scheduler_thread
    _scheduler = scheduler
    _scheduler_thread = threading.current_thread()


class Observable(Generic[T]):
    """A single observable value with automatic dependency tracking."""

    __slots__ = ("_id",)

    def __init__(self, value: T) -> None:
        self._id = _anchor.new_id()
        _anchor.values[self._id] = value
        _anchor.observers[self._id] = set()

    def get(self) -> T:
        """Read the value. If inside a derivation, registers the dependency."""
        derivation = current_derivation.get()
        if derivation is not None:
            _anchor.observers[self._id].add(derivation)
            derivation._dependencies.add(self)
        return _anchor.values[self._id]

    def set(self, value: T) -> None:
        """Write a new value. Auto-marshals from background threads."""
        if _scheduler is not None and threading.current_thread() != _scheduler_thread:
            _scheduler(lambda v=value: self._set_direct(v))
        else:
            self._set_direct(value)

    def _set_direct(self, value: T) -> None:
        """Set value and notify. Always runs on the scheduler thread."""
        old = _anchor.values[self._id]
        if old is not value and old != value:
            _anchor.values[self._id] = value
            self._notify()

    def _notify(self) -> None:
        """Schedule all observers for re-evaluation."""
        for observer in list(_anchor.observers[self._id]):
            schedule(observer)

    def _remove_observer(self, observer) -> None:
        """Remove an observer. Called during dependency cleanup."""
        _anchor.observers[self._id].discard(observer)

    def __repr__(self) -> str:
        return f"Observable({_anchor.values[self._id]!r})"


class ObservableList(Generic[T]):
    """An observable list that tracks reads and notifies on mutation.

    Any read operation (iteration, indexing, len) registers a dependency.
    Any mutation (append, extend, __setitem__, etc.) notifies observers.
    """

    __slots__ = ("_id",)

    def __init__(self, items: list[T] | None = None) -> None:
        self._id = _anchor.new_id()
        _anchor.values[self._id] = list(items) if items else []
        _anchor.observers[self._id] = set()

    @property
    def _items(self) -> list[T]:
        return _anchor.values[self._id]

    def _track(self) -> None:
        """Register current derivation as an observer."""
        derivation = current_derivation.get()
        if derivation is not None:
            _anchor.observers[self._id].add(derivation)
            derivation._dependencies.add(self)

    def _notify(self) -> None:
        for observer in list(_anchor.observers[self._id]):
            schedule(observer)

    def _remove_observer(self, observer) -> None:
        _anchor.observers[self._id].discard(observer)

    # --- Read operations (track) ---

    def __getitem__(self, index: int) -> T:
        self._track()
        return self._items[index]

    def __len__(self) -> int:
        self._track()
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        self._track()
        return iter(self._items)

    def __contains__(self, item: T) -> bool:
        self._track()
        return item in self._items

    def __bool__(self) -> bool:
        self._track()
        return bool(self._items)

    # --- Write operations (notify) ---

    def append(self, item: T) -> None:
        self._items.append(item)
        self._notify()

    def extend(self, items) -> None:
        self._items.extend(items)
        self._notify()

    def insert(self, index: int, item: T) -> None:
        self._items.insert(index, item)
        self._notify()

    def pop(self, index: int = -1) -> T:
        result = self._items.pop(index)
        self._notify()
        return result

    def remove(self, item: T) -> None:
        self._items.remove(item)
        self._notify()

    def clear(self) -> None:
        self._items.clear()
        self._notify()

    def __setitem__(self, index: int, value: T) -> None:
        self._items[index] = value
        self._notify()

    def __delitem__(self, index: int) -> None:
        del self._items[index]
        self._notify()

    def __repr__(self) -> str:
        return f"ObservableList({self._items!r})"


class ObservableDict(Generic[KT, VT]):
    """An observable dict that tracks reads and notifies on mutation."""

    __slots__ = ("_id",)

    def __init__(self, data: dict[KT, VT] | None = None) -> None:
        self._id = _anchor.new_id()
        _anchor.values[self._id] = dict(data) if data else {}
        _anchor.observers[self._id] = set()

    @property
    def _data(self) -> dict[KT, VT]:
        return _anchor.values[self._id]

    def _track(self) -> None:
        derivation = current_derivation.get()
        if derivation is not None:
            _anchor.observers[self._id].add(derivation)
            derivation._dependencies.add(self)

    def _notify(self) -> None:
        for observer in list(_anchor.observers[self._id]):
            schedule(observer)

    def _remove_observer(self, observer) -> None:
        _anchor.observers[self._id].discard(observer)

    # --- Read operations (track) ---

    def __getitem__(self, key: KT) -> VT:
        self._track()
        return self._data[key]

    def get(self, key: KT, default: VT | None = None) -> VT | None:
        self._track()
        return self._data.get(key, default)

    def __contains__(self, key: KT) -> bool:
        self._track()
        return key in self._data

    def __len__(self) -> int:
        self._track()
        return len(self._data)

    def __iter__(self) -> Iterator[KT]:
        self._track()
        return iter(self._data)

    def keys(self):
        self._track()
        return self._data.keys()

    def values(self):
        self._track()
        return self._data.values()

    def items(self):
        self._track()
        return self._data.items()

    def __bool__(self) -> bool:
        self._track()
        return bool(self._data)

    # --- Write operations (notify) ---

    def __setitem__(self, key: KT, value: VT) -> None:
        self._data[key] = value
        self._notify()

    def __delitem__(self, key: KT) -> None:
        del self._data[key]
        self._notify()

    def pop(self, key: KT, *args) -> VT:
        result = self._data.pop(key, *args)
        self._notify()
        return result

    def update(self, other=None, **kwargs) -> None:
        if other:
            self._data.update(other)
        if kwargs:
            self._data.update(kwargs)
        self._notify()

    def clear(self) -> None:
        self._data.clear()
        self._notify()

    def setdefault(self, key: KT, default: VT | None = None) -> VT:
        if key not in self._data:
            self._data[key] = default
            self._notify()
        return self._data[key]

    def __repr__(self) -> str:
        return f"ObservableDict({self._data!r})"
