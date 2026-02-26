"""Tests for Store."""

from snarfx import Store, autorun, reaction


class TestStore:
    def test_creation_from_schema(self):
        s = Store({"x": 10, "y": "hello"})
        assert s.get("x") == 10
        assert s.get("y") == "hello"

    def test_initial_overrides(self):
        s = Store({"x": 10, "y": "hello"}, initial={"x": 99})
        assert s.get("x") == 99
        assert s.get("y") == "hello"

    def test_get_nonexistent(self):
        s = Store({"x": 1})
        assert s.get("nope") is None

    def test_set(self):
        s = Store({"x": 0})
        s.set("x", 42)
        assert s.get("x") == 42

    def test_set_nonexistent_is_noop(self):
        s = Store({"x": 0})
        s.set("nope", 99)  # no-op, no error

    def test_update_batches(self):
        s = Store({"x": 0, "y": 0})
        log = []
        autorun(lambda: log.append((s.get("x"), s.get("y"))))
        assert log == [(0, 0)]
        s.update({"x": 1, "y": 2})
        assert log == [(0, 0), (1, 2)]  # single batch

    def test_reactive_tracking(self):
        s = Store({"count": 0})
        log = []
        autorun(lambda: log.append(s.get("count")))
        assert log == [0]
        s.set("count", 1)
        assert log == [0, 1]

    def test_reconcile_adds_keys(self):
        s = Store({"x": 1})
        s.reconcile({"x": 1, "z": 99}, lambda store: [])
        assert s.get("z") == 99
        assert s.get("x") == 1  # preserved

    def test_reconcile_preserves_values(self):
        s = Store({"x": 1})
        s.set("x", 42)
        s.reconcile({"x": 1}, lambda store: [])
        assert s.get("x") == 42

    def test_reconcile_disposes_old_reactions(self):
        s = Store({"x": 0})
        log = []

        def setup(store):
            return [reaction(lambda: store.get("x"), lambda v: log.append(v))]

        s.reconcile({"x": 0}, setup)
        s.set("x", 1)
        assert log == [1]

        # Reconcile again — old reaction should be disposed
        log2 = []

        def setup2(store):
            return [reaction(lambda: store.get("x"), lambda v: log2.append(v))]

        s.reconcile({"x": 0}, setup2)
        s.set("x", 2)
        assert log2 == [2]
        assert log == [1]  # old reaction didn't fire

    def test_dispose(self):
        s = Store({"x": 0})
        log = []

        def setup(store):
            return [reaction(lambda: store.get("x"), lambda v: log.append(v))]

        s.reconcile({"x": 0}, setup)
        s.set("x", 1)
        assert log == [1]

        s.dispose()
        s.set("x", 2)
        assert log == [1]  # reactions disposed
