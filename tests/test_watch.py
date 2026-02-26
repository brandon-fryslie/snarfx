"""Tests for watch() — managed daemon threads with auto-marshaled Observable.set()."""

import threading
import time

from snarfx import Observable, watch, reaction
from snarfx.observable import set_scheduler, _scheduler, _scheduler_thread
import snarfx.observable as _obs_mod


def _with_scheduler(fn):
    """Run fn with a sync scheduler set on the current thread, then restore."""
    old_sched, old_thread = _obs_mod._scheduler, _obs_mod._scheduler_thread
    _obs_mod._scheduler = lambda f: f()
    _obs_mod._scheduler_thread = threading.current_thread()
    try:
        fn()
    finally:
        _obs_mod._scheduler = old_sched
        _obs_mod._scheduler_thread = old_thread


class TestAutoMarshal:
    """Observable.set() auto-marshals from background threads."""

    def test_main_thread_is_synchronous(self):
        """set() from the scheduler thread is immediate."""
        _with_scheduler(lambda: None)  # ensure scheduler is set
        v = Observable(0)
        old_sched, old_thread = _obs_mod._scheduler, _obs_mod._scheduler_thread
        _obs_mod._scheduler = lambda f: f()
        _obs_mod._scheduler_thread = threading.current_thread()
        try:
            v.set(42)
            assert v.get() == 42
        finally:
            _obs_mod._scheduler = old_sched
            _obs_mod._scheduler_thread = old_thread

    def test_background_thread_marshals(self):
        """set() from a background thread goes through scheduler."""
        calls = []
        old_sched, old_thread = _obs_mod._scheduler, _obs_mod._scheduler_thread
        _obs_mod._scheduler = lambda f: (calls.append(f), f())
        _obs_mod._scheduler_thread = threading.current_thread()
        try:
            v = Observable(0)
            done = threading.Event()

            def bg():
                v.set(99)
                done.set()

            threading.Thread(target=bg).start()
            done.wait(timeout=2)
            assert len(calls) == 1
            assert v.get() == 99
        finally:
            _obs_mod._scheduler = old_sched
            _obs_mod._scheduler_thread = old_thread

    def test_no_scheduler_is_direct(self):
        """Without scheduler, set() works directly (no marshaling)."""
        old_sched, old_thread = _obs_mod._scheduler, _obs_mod._scheduler_thread
        _obs_mod._scheduler = None
        _obs_mod._scheduler_thread = None
        try:
            v = Observable(0)
            v.set(42)
            assert v.get() == 42
        finally:
            _obs_mod._scheduler = old_sched
            _obs_mod._scheduler_thread = old_thread


class TestWatch:
    """watch() runs a function in a daemon thread."""

    def test_function_runs(self):
        ran = threading.Event()
        handle = watch(lambda: ran.set())
        assert ran.wait(timeout=2)

    def test_dispose_flag(self):
        handle = watch(lambda: None)
        assert not handle.disposed
        handle.dispose()
        assert handle.disposed

    def test_observable_updated_from_watch(self):
        """Integration: watch + Observable with auto-marshal."""
        old_sched, old_thread = _obs_mod._scheduler, _obs_mod._scheduler_thread
        _obs_mod._scheduler = lambda f: f()
        _obs_mod._scheduler_thread = threading.main_thread()
        try:
            result = Observable(None)
            done = threading.Event()

            def work():
                result.set(42)
                done.set()

            watch(work)
            done.wait(timeout=2)
            assert result.get() == 42
        finally:
            _obs_mod._scheduler = old_sched
            _obs_mod._scheduler_thread = old_thread

    def test_poll_loop_exits_on_condition(self):
        """Typical polling pattern: loop until external condition changes."""
        old_sched, old_thread = _obs_mod._scheduler, _obs_mod._scheduler_thread
        _obs_mod._scheduler = lambda f: f()
        _obs_mod._scheduler_thread = threading.main_thread()
        try:
            alive = Observable(True)
            condition = threading.Event()

            def poll():
                while not condition.is_set():
                    time.sleep(0.01)
                alive.set(False)

            watch(poll)
            assert alive.get() is True
            condition.set()
            time.sleep(0.1)
            assert alive.get() is False
        finally:
            _obs_mod._scheduler = old_sched
            _obs_mod._scheduler_thread = old_thread


class TestWatchWithReaction:
    """Integration: watch + Observable + reaction."""

    def test_reaction_fires_on_watch_update(self):
        old_sched, old_thread = _obs_mod._scheduler, _obs_mod._scheduler_thread
        _obs_mod._scheduler = lambda f: f()
        _obs_mod._scheduler_thread = threading.main_thread()
        try:
            health = Observable(True)
            effects = []
            done = threading.Event()

            reaction(lambda: health.get(), lambda v: effects.append(v))

            def check():
                health.set(False)
                done.set()

            watch(check)
            done.wait(timeout=2)
            assert effects == [False]
        finally:
            _obs_mod._scheduler = old_sched
            _obs_mod._scheduler_thread = old_thread
