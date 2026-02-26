"""Hot-reload-aware store. Opt-in — import only if you need hot-reload support."""

import logging

from snarfx.observable import Observable
from snarfx.store import Store

logger = logging.getLogger("snarfx.hot_reload")


class HotReloadStore(Store):
    """Store that survives module reloads via safe reconciliation.

    Same API as Store. Adds:
    - Exception safety: reconcile catches and logs reaction setup failures
    - Logging: reconcile events are clearly logged
    - Degraded operation: if reconcile fails, store continues with values intact
    """

    def reconcile(self, schema, setup_fn):
        """Safe reconciliation — catches exceptions, logs, never crashes."""
        # Add new keys
        new_keys = []
        for key, default in schema.items():
            if key not in self._observables:
                self._observables[key] = Observable(default)
                new_keys.append(key)

        # Dispose old reactions
        old_count = len(self._reaction_disposers)
        self._dispose_reactions()

        # Register new reactions with safety
        try:
            self._reaction_disposers = setup_fn(self) or []
            new_count = len(self._reaction_disposers)
            logger.info(
                "Reconciled: %d new keys, %d->%d reactions",
                len(new_keys), old_count, new_count,
            )
        except Exception:
            logger.exception("Failed to register reactions during reconcile")
            # Store continues — values intact, no reactions (degraded)
            self._reaction_disposers = []
