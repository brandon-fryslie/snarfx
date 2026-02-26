"""Dependency tracking engine — the heart of SnarfX.

Uses contextvars to track which observables are read during a computed/reaction
evaluation, building the dependency graph automatically.

Batching: mutations inside an @action or `with transaction()` accumulate
invalidations and flush them once at the end, ensuring glitch-free updates.
"""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snarfx.computed import Computed
    from snarfx.reaction import Reaction

    Derivation = Computed | Reaction

# The currently-evaluating derivation (computed or reaction).
# When set, any Observable.get() call registers itself as a dependency.
current_derivation: contextvars.ContextVar[Derivation | None] = contextvars.ContextVar(
    "current_derivation", default=None
)

# Batch depth counter. When > 0, invalidations are deferred.
_batch_depth: int = 0

# Derivations that were invalidated during a batch, awaiting flush.
_pending: set[Derivation] = set()


def begin_batch() -> None:
    """Enter a batching scope. Nested batches are supported."""
    global _batch_depth
    _batch_depth += 1


def end_batch() -> None:
    """Exit a batching scope. When the outermost scope exits, flush pending derivations."""
    global _batch_depth
    _batch_depth -= 1
    if _batch_depth == 0:
        _flush_pending()


def schedule(derivation: Derivation) -> None:
    """Schedule a derivation for re-evaluation.

    If inside a batch, defers. Otherwise, runs immediately.
    """
    if _batch_depth > 0:
        _pending.add(derivation)
    else:
        derivation._run()


def _flush_pending() -> None:
    """Run all pending derivations. Handles derivations scheduled during flush."""
    while _pending:
        # Snapshot and clear — derivations may schedule new ones during run.
        batch = list(_pending)
        _pending.clear()
        for derivation in batch:
            derivation._run()


def get_pending_count() -> int:
    """Number of derivations waiting to run. Useful for testing."""
    return len(_pending)
