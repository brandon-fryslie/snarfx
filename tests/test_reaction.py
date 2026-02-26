"""Tests for Reaction, autorun, and reaction."""

from snarfx import Observable, autorun, reaction


class TestAutorun:
    def test_runs_immediately(self):
        o = Observable(10)
        log = []
        autorun(lambda: log.append(o.get()))
        assert log == [10]

    def test_reruns_on_change(self):
        o = Observable(10)
        log = []
        autorun(lambda: log.append(o.get()))
        o.set(20)
        assert log == [10, 20]

    def test_dispose_stops(self):
        o = Observable(10)
        log = []
        r = autorun(lambda: log.append(o.get()))
        r.dispose()
        o.set(20)
        assert log == [10]  # no additional run


class TestReaction:
    def test_no_initial_effect(self):
        """Without fire_immediately, effect doesn't run on setup."""
        o = Observable("a")
        effects = []
        reaction(lambda: o.get(), lambda v: effects.append(v))
        assert effects == []

    def test_fires_on_change(self):
        o = Observable("a")
        effects = []
        reaction(lambda: o.get(), lambda v: effects.append(v))
        o.set("b")
        assert effects == ["b"]

    def test_fire_immediately(self):
        o = Observable("a")
        effects = []
        reaction(lambda: o.get(), lambda v: effects.append(v), fire_immediately=True)
        assert effects == ["a"]

    def test_dedup_effect(self):
        """Effect only fires when data_fn result actually changes."""
        o = Observable(1)
        effects = []
        # data_fn always returns "even" or "odd"
        reaction(
            lambda: "even" if o.get() % 2 == 0 else "odd",
            lambda v: effects.append(v),
        )
        o.set(3)  # still odd
        assert effects == []  # data_fn returned same "odd"
        o.set(4)  # now even
        assert effects == ["even"]

    def test_dispose(self):
        o = Observable(1)
        effects = []
        r = reaction(lambda: o.get(), lambda v: effects.append(v))
        o.set(2)
        assert effects == [2]
        r.dispose()
        o.set(3)
        assert effects == [2]  # no more effects
