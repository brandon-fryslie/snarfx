"""Tests for snarfx.textual — Textual integration layer."""

import threading

import pytest
from textual.css.query import NoMatches

from snarfx import Observable
from snarfx import textual as stx


class _MockApp:
    """Minimal mock matching the Textual App interface stx needs."""

    def __init__(self, *, is_running=True):
        self.is_running = is_running
        self._call_from_thread_log = []

    def call_from_thread(self, fn, *args):
        self._call_from_thread_log.append((fn, args))
        fn(*args)


class TestReaction:
    def test_skips_when_not_running(self):
        app = _MockApp(is_running=False)
        o = Observable(1)
        effects = []
        stx.reaction(app, lambda: o.get(), lambda v: effects.append(v))
        o.set(2)
        assert effects == []

    def test_skips_during_pause(self):
        app = _MockApp()
        o = Observable(1)
        effects = []
        stx.reaction(app, lambda: o.get(), lambda v: effects.append(v))
        with stx.pause(app):
            o.set(2)
        assert effects == []

    def test_fires_when_safe(self):
        app = _MockApp()
        o = Observable(1)
        effects = []
        stx.reaction(app, lambda: o.get(), lambda v: effects.append(v))
        o.set(2)
        assert effects == [2]

    def test_catches_nomatch(self):
        """NoMatches from widget queries are silently swallowed."""
        app = _MockApp()
        o = Observable(1)

        def _raise_nomatch(v):
            raise NoMatches("StatusFooter")

        # Should not raise
        r = stx.reaction(app, lambda: o.get(), _raise_nomatch)
        o.set(2)
        r.dispose()

    def test_propagates_real_errors(self):
        """Non-NoMatches exceptions propagate normally."""
        app = _MockApp()
        o = Observable(1)

        def _raise_value_error(v):
            raise ValueError("boom")

        stx.reaction(app, lambda: o.get(), _raise_value_error)
        with pytest.raises(ValueError, match="boom"):
            o.set(2)

    def test_dispose_stops_reaction(self):
        app = _MockApp()
        o = Observable(1)
        effects = []
        r = stx.reaction(app, lambda: o.get(), lambda v: effects.append(v))
        o.set(2)
        assert effects == [2]
        r.dispose()
        o.set(3)
        assert effects == [2]

    def test_thread_marshal(self):
        """Triggers from background thread use call_from_thread."""
        app = _MockApp()
        o = Observable(1)
        effects = []
        stx.reaction(app, lambda: o.get(), lambda v: effects.append(v))

        # Trigger from a different thread
        def _bg():
            o.set(2)

        t = threading.Thread(target=_bg)
        t.start()
        t.join()

        assert effects == [2]
        # Verify call_from_thread was used (at least once)
        assert len(app._call_from_thread_log) >= 1


class TestAutorun:
    def test_skips_during_pause(self):
        app = _MockApp()
        o = Observable(1)
        log = []

        stx.autorun(app, lambda: log.append(o.get()))
        # autorun fires immediately on setup
        assert log == [1]

        with stx.pause(app):
            o.set(2)
        # Skipped during pause
        assert log == [1]

    def test_catches_nomatch(self):
        """NoMatches from widget queries are silently swallowed."""
        app = _MockApp()
        o = Observable(1)
        call_count = [0]

        def _fn():
            call_count[0] += 1
            o.get()  # track dependency
            if call_count[0] > 1:
                raise NoMatches("Widget")

        # Initial run succeeds (call_count becomes 1)
        stx.autorun(app, _fn)
        assert call_count[0] == 1

        # Second run raises NoMatches — silently caught
        o.set(2)
        assert call_count[0] == 2

    def test_fires_when_safe(self):
        app = _MockApp()
        o = Observable(1)
        log = []
        stx.autorun(app, lambda: log.append(o.get()))
        o.set(2)
        assert log == [1, 2]


class TestPause:
    def test_pause_restores_on_exception(self):
        app = _MockApp()
        assert stx.is_safe(app)

        with pytest.raises(RuntimeError):
            with stx.pause(app):
                assert not stx.is_safe(app)
                raise RuntimeError("oops")

        # Restored despite exception
        assert stx.is_safe(app)

    def test_pause_does_not_mutate_app(self):
        """// [LAW:no-shared-mutable-globals] pause state lives in the module, not on the app.

        This test prevents regression to setting attributes on external objects.
        """
        app = _MockApp()
        attrs_before = set(vars(app))
        with stx.pause(app):
            attrs_during = set(vars(app))
        attrs_after = set(vars(app))
        assert attrs_before == attrs_during, (
            f"pause() added attributes to app: {attrs_during - attrs_before}"
        )
        assert attrs_before == attrs_after

    def test_multiple_apps_independent(self):
        """Pausing one app does not affect another."""
        app_a = _MockApp()
        app_b = _MockApp()
        with stx.pause(app_a):
            assert not stx.is_safe(app_a)
            assert stx.is_safe(app_b)
