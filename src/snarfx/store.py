"""Store — key-based Observable container with reaction lifecycle.

A Store wraps a schema of named Observables and manages reaction disposers.
reconcile() supports schema evolution: add new keys and re-register reactions
without losing existing values.
"""

from __future__ import annotations

from snarfx.observable import Observable
from snarfx.action import action


class Store:
    """Key-based Observable container with reaction lifecycle."""

    def __init__(self, schema: dict[str, object], initial: dict | None = None) -> None:
        self._observables: dict[str, Observable] = {}
        self._reaction_disposers: list = []
        for key, default in schema.items():
            value = initial.get(key, default) if initial else default
            self._observables[key] = Observable(value)

    def get(self, key: str) -> object:
        obs = self._observables.get(key)
        return obs.get() if obs is not None else None

    def set(self, key: str, value: object) -> None:
        obs = self._observables.get(key)
        if obs is not None:
            obs.set(value)

    @action
    def update(self, values: dict) -> None:
        for key, value in values.items():
            self.set(key, value)

    def reconcile(self, schema: dict[str, object], setup_fn) -> None:
        """Schema evolution: add new keys, re-register reactions.

        Existing Observable values are untouched. New keys get defaults.
        Old reactions are disposed. setup_fn(store) -> list[disposer] registers new ones.
        """
        for key, default in schema.items():
            if key not in self._observables:
                self._observables[key] = Observable(default)
        self._dispose_reactions()
        self._reaction_disposers = setup_fn(self) or []

    def _dispose_reactions(self):
        for d in self._reaction_disposers:
            d.dispose()
        self._reaction_disposers.clear()

    def dispose(self):
        self._dispose_reactions()
