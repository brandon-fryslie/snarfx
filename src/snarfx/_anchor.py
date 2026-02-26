"""Data anchor — plain Python structures that hold all reactive state.

This module stores the raw data for all Observables, Computeds, and Reactions.
Separating data from behavior means the behavior modules can be replaced
while the data persists.
"""

import itertools

# Observable state
values: dict[int, object] = {}
observers: dict[int, set] = {}  # obs_id -> set of derivation IDs

# Derivation state (Computed + Reaction)
dependencies: dict[int, set] = {}  # deriv_id -> set of observable-like IDs
dirty_flags: dict[int, bool] = {}
cached_values: dict[int, object] = {}
derivation_fns: dict[int, object] = {}  # deriv_id -> callable
disposed: dict[int, bool] = {}

# ID generation — itertools.count is thread-safe (C-level GIL atomic)
_id_counter = itertools.count(1)


def new_id() -> int:
    return next(_id_counter)
