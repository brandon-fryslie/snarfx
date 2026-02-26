"""Tests for Computed values."""

from snarfx import Observable, Computed, computed, autorun


class TestComputed:
    def test_lazy_eval(self):
        call_count = 0
        o = Observable(5)

        def fn():
            nonlocal call_count
            call_count += 1
            return o.get() * 2

        c = Computed(fn)
        assert call_count == 0  # not yet evaluated
        assert c.get() == 10
        assert call_count == 1

    def test_caches_until_dirty(self):
        call_count = 0
        o = Observable(5)

        def fn():
            nonlocal call_count
            call_count += 1
            return o.get() * 2

        c = Computed(fn)
        c.get()
        c.get()
        assert call_count == 1  # cached, no re-eval

    def test_invalidation(self):
        o = Observable(5)
        c = Computed(lambda: o.get() * 2)
        assert c.get() == 10
        o.set(10)
        assert c.get() == 20

    def test_dependency_tracking(self):
        """Computed tracks dependencies dynamically."""
        flag = Observable(True)
        a = Observable(1)
        b = Observable(2)

        c = Computed(lambda: a.get() if flag.get() else b.get())
        assert c.get() == 1

        flag.set(False)
        assert c.get() == 2  # now depends on b, not a

    def test_chained_computed(self):
        o = Observable(3)
        doubled = Computed(lambda: o.get() * 2)
        quadrupled = Computed(lambda: doubled.get() * 2)
        assert quadrupled.get() == 12
        o.set(5)
        assert quadrupled.get() == 20

    def test_dispose(self):
        o = Observable(5)
        c = Computed(lambda: o.get() * 2)
        c.get()
        c.dispose()
        # After dispose, the computed is inert
        o.set(10)
        # get() re-evaluates from scratch since dispose cleared everything
        assert c.get() == 20  # still works, just re-evals

    def test_propagates_to_reactions(self):
        """Computed invalidation propagates to downstream reactions."""
        o = Observable(5)
        c = Computed(lambda: o.get() * 2)
        log = []
        autorun(lambda: log.append(c.get()))
        assert log == [10]
        o.set(10)
        assert log == [10, 20]


class TestComputedDecorator:
    def test_decorator_factory(self):
        o = Observable(7)

        @computed
        def doubled():
            return o.get() * 2

        assert doubled.get() == 14
        o.set(3)
        assert doubled.get() == 6
