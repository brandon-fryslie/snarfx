"""Tests for action batching and transaction context manager."""

from snarfx import Observable, action, transaction, autorun


class TestAction:
    def test_batches_updates(self):
        a = Observable(0)
        b = Observable(0)
        log = []
        autorun(lambda: log.append((a.get(), b.get())))
        assert log == [(0, 0)]

        @action
        def update_both():
            a.set(1)
            b.set(2)

        update_both()
        # Should see (1, 2) not intermediate (1, 0)
        assert log == [(0, 0), (1, 2)]

    def test_nested_actions(self):
        o = Observable(0)
        log = []
        autorun(lambda: log.append(o.get()))

        @action
        def outer():
            o.set(1)

            @action
            def inner():
                o.set(2)

            inner()
            o.set(3)

        outer()
        # Only fires after outermost action completes
        assert log == [0, 3]

    def test_preserves_return_value(self):
        @action
        def compute():
            return 42

        assert compute() == 42


class TestTransaction:
    def test_batches_updates(self):
        a = Observable(0)
        b = Observable(0)
        log = []
        autorun(lambda: log.append((a.get(), b.get())))

        with transaction():
            a.set(10)
            b.set(20)

        assert log == [(0, 0), (10, 20)]

    def test_nested_transactions(self):
        o = Observable(0)
        log = []
        autorun(lambda: log.append(o.get()))

        with transaction():
            o.set(1)
            with transaction():
                o.set(2)
            o.set(3)

        assert log == [0, 3]
