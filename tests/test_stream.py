"""Tests for EventStream — push-based event stream with operator chaining."""

import threading
import time

from snarfx import EventStream


class TestEmitSubscribe:
    """Core emit/subscribe behavior."""

    def test_subscribe_receives_emitted_values(self):
        stream = EventStream()
        received = []
        stream.subscribe(lambda v: received.append(v))
        stream.emit(1)
        stream.emit(2)
        assert received == [1, 2]

    def test_multiple_subscribers(self):
        stream = EventStream()
        a, b = [], []
        stream.subscribe(lambda v: a.append(v))
        stream.subscribe(lambda v: b.append(v))
        stream.emit("x")
        assert a == ["x"]
        assert b == ["x"]

    def test_unsubscribe(self):
        stream = EventStream()
        received = []
        unsub = stream.subscribe(lambda v: received.append(v))
        stream.emit(1)
        unsub()
        stream.emit(2)
        assert received == [1]

    def test_unsubscribe_idempotent(self):
        stream = EventStream()
        unsub = stream.subscribe(lambda v: None)
        unsub()
        unsub()  # should not raise


class TestMap:
    """map() operator."""

    def test_transforms_values(self):
        stream = EventStream()
        doubled = stream.map(lambda v: v * 2)
        received = []
        doubled.subscribe(lambda v: received.append(v))
        stream.emit(3)
        stream.emit(5)
        assert received == [6, 10]

    def test_chained_maps(self):
        stream = EventStream()
        result = stream.map(lambda v: v + 1).map(lambda v: v * 10)
        received = []
        result.subscribe(lambda v: received.append(v))
        stream.emit(2)
        assert received == [30]


class TestFilter:
    """filter() operator."""

    def test_passes_matching_values(self):
        stream = EventStream()
        evens = stream.filter(lambda v: v % 2 == 0)
        received = []
        evens.subscribe(lambda v: received.append(v))
        stream.emit(1)
        stream.emit(2)
        stream.emit(3)
        stream.emit(4)
        assert received == [2, 4]

    def test_filter_then_map(self):
        stream = EventStream()
        result = stream.filter(lambda v: v > 0).map(lambda v: v * 10)
        received = []
        result.subscribe(lambda v: received.append(v))
        stream.emit(-1)
        stream.emit(3)
        assert received == [30]


class TestDebounce:
    """debounce() operator."""

    def test_coalesces_rapid_events(self):
        stream = EventStream()
        debounced = stream.debounce(0.05)
        received = []
        done = threading.Event()

        def on_value(v):
            received.append(v)
            done.set()

        debounced.subscribe(on_value)

        # Rapid burst — only the last should fire
        stream.emit(1)
        stream.emit(2)
        stream.emit(3)

        done.wait(timeout=1)
        assert received == [3]

    def test_separate_bursts(self):
        stream = EventStream()
        debounced = stream.debounce(0.03)
        received = []
        event = threading.Event()

        def on_value(v):
            received.append(v)
            event.set()

        debounced.subscribe(on_value)

        # First burst
        stream.emit("a")
        event.wait(timeout=1)
        event.clear()

        # Second burst after quiet period
        stream.emit("b")
        event.wait(timeout=1)

        assert received == ["a", "b"]


class TestDispose:
    """dispose() tears down streams and children."""

    def test_emit_after_dispose_is_noop(self):
        stream = EventStream()
        received = []
        stream.subscribe(lambda v: received.append(v))
        stream.dispose()
        stream.emit(1)
        assert received == []

    def test_dispose_propagates_to_children(self):
        parent = EventStream()
        child = parent.map(lambda v: v)
        grandchild = child.filter(lambda v: True)

        parent.dispose()

        assert child._disposed
        assert grandchild._disposed

    def test_child_dispose_does_not_affect_parent(self):
        parent = EventStream()
        child = parent.map(lambda v: v)
        received_parent = []
        parent.subscribe(lambda v: received_parent.append(v))

        child.dispose()

        parent.emit(1)
        assert received_parent == [1]
        assert not parent._disposed
