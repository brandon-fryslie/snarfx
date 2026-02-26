"""SnarfX: MobX-inspired reactive state management for Python."""

from importlib.metadata import version as _version

__version__ = _version("snarfx")

from snarfx._tracking import get_pending_count
from snarfx.observable import Observable, ObservableList, ObservableDict, set_scheduler
from snarfx.computed import Computed, computed
from snarfx.reaction import Reaction, autorun, reaction
from snarfx.action import action, transaction
from snarfx.store import Store
from snarfx.watch import watch, WatchHandle
from snarfx.stream import EventStream
# hot_reload NOT auto-imported — opt-in only

__all__ = [
    "Observable",
    "ObservableList",
    "ObservableDict",
    "Computed",
    "computed",
    "Reaction",
    "autorun",
    "reaction",
    "action",
    "transaction",
    "get_pending_count",
    "Store",
    "set_scheduler",
    "watch",
    "WatchHandle",
    "EventStream",
]
