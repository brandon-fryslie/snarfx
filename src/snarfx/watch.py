"""watch() — run a function in a managed daemon thread.

Observable.set() auto-marshals cross-thread mutations (see set_scheduler),
so watch() is purely about thread lifecycle. Returns a WatchHandle for
cleanup via .dispose().

// [LAW:dataflow-not-control-flow] The background function mutates Observables
// directly. Values flow through the reactive graph, not through callbacks.
"""

from __future__ import annotations

from threading import Thread


class WatchHandle:
    """Disposable handle for a managed daemon thread."""

    __slots__ = ("_disposed",)

    def __init__(self):
        self._disposed = False

    @property
    def disposed(self) -> bool:
        return self._disposed

    def dispose(self) -> None:
        """Signal the thread to stop. Check .disposed in your loop."""
        self._disposed = True


def watch(fn) -> WatchHandle:
    """Run fn in a daemon thread. Returns WatchHandle.

    The function can call Observable.set() freely — mutations are
    auto-marshaled to the main thread. Use handle.disposed to exit
    long-running loops early.

    Usage:
        alive = Observable(True)

        def poll():
            while not handle.disposed and validate():
                time.sleep(2)
            alive.set(False)

        handle = watch(poll)
    """
    handle = WatchHandle()
    Thread(target=fn, daemon=True).start()
    return handle
