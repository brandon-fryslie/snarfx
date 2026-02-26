"""Tests for HotReloadStore — safe reconciliation."""

import logging

from snarfx.hot_reload import HotReloadStore
from snarfx import reaction


class TestHotReloadStore:
    def test_creation(self):
        s = HotReloadStore({"a": 1, "b": "x"})
        assert s.get("a") == 1
        assert s.get("b") == "x"

    def test_safe_reconcile_success(self):
        s = HotReloadStore({"a": 1})
        log = []

        def setup(store):
            return [reaction(lambda: store.get("a"), lambda v: log.append(v))]

        s.reconcile({"a": 1, "b": 2}, setup)
        assert s.get("b") == 2
        s.set("a", 10)
        assert log == [10]

    def test_safe_reconcile_failure(self, caplog):
        """When setup_fn raises, store continues with values intact, no reactions."""
        s = HotReloadStore({"a": 1})
        s.set("a", 42)

        def bad_setup(store):
            raise RuntimeError("boom")

        with caplog.at_level(logging.ERROR, logger="snarfx.hot_reload"):
            s.reconcile({"a": 1, "c": 3}, bad_setup)

        assert s.get("a") == 42  # value preserved
        assert s.get("c") == 3  # new key added
        assert s._reaction_disposers == []  # degraded mode
        assert "Failed to register reactions" in caplog.text

    def test_reconcile_logs_info(self, caplog):
        s = HotReloadStore({"a": 1})

        with caplog.at_level(logging.INFO, logger="snarfx.hot_reload"):
            s.reconcile({"a": 1, "b": 2}, lambda store: [])

        assert "Reconciled" in caplog.text
        assert "1 new keys" in caplog.text

    def test_is_a_store(self):
        """HotReloadStore is a proper subclass of Store."""
        from snarfx import Store
        s = HotReloadStore({"x": 0})
        assert isinstance(s, Store)

    def test_update_batching(self):
        """Inherited Store.update batching works."""
        s = HotReloadStore({"x": 0, "y": 0})
        log = []

        from snarfx import autorun
        autorun(lambda: log.append((s.get("x"), s.get("y"))))
        assert log == [(0, 0)]
        s.update({"x": 1, "y": 2})
        assert log == [(0, 0), (1, 2)]
