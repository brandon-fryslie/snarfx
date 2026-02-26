"""Textual integration for SnarfX. Opt-in — requires textual.

// [LAW:single-enforcer] Guard + NoMatches + thread-marshal enforced here, not at callsites.
// [LAW:locality-or-seam] Textual coupling isolated in this module — core SnarfX stays agnostic.
// [LAW:no-shared-mutable-globals] _paused_apps has single owner (this module), explicit API
//   (pause/is_safe), documented invariant (id present ↔ inside pause context).
"""

import threading
from contextlib import contextmanager

from textual.css.query import NoMatches
from snarfx import autorun as _autorun, reaction as _reaction

# Module-owned pause state — keyed by id(app) so multiple apps work in tests.
_paused_apps: set[int] = set()


@contextmanager
def pause(app):
    """Suspend guarded reactions during widget replacement."""
    key = id(app)
    _paused_apps.add(key)
    try:
        yield
    finally:
        _paused_apps.discard(key)


def is_safe(app) -> bool:
    """Is the widget tree in a queryable state?"""
    return app.is_running and id(app) not in _paused_apps


def reaction(app, data_fn, effect_fn, *, fire_immediately=False):
    """reaction() that safely bridges to Textual widgets.

    Guards against firing during pause/not-running, catches NoMatches
    from widget queries, and marshals cross-thread calls via call_from_thread.
    """
    _main = threading.get_ident()

    def _guarded(value):
        if not is_safe(app):
            return
        if threading.get_ident() != _main:
            app.call_from_thread(_safe, value)
        else:
            _safe(value)

    def _safe(value):
        try:
            effect_fn(value)
        except NoMatches:
            pass

    return _reaction(data_fn, _guarded, fire_immediately=fire_immediately)


def autorun(app, fn):
    """autorun() that safely bridges to Textual widgets.

    Guards against firing during pause/not-running, catches NoMatches
    from widget queries, and marshals cross-thread calls via call_from_thread.
    """
    _main = threading.get_ident()

    def _guarded():
        if not is_safe(app):
            return
        if threading.get_ident() != _main:
            app.call_from_thread(_safe)
        else:
            _safe()

    def _safe():
        try:
            fn()
        except NoMatches:
            pass

    return _autorun(_guarded)
