"""Tests for Observable, ObservableList, and ObservableDict."""

from snarfx import Observable, ObservableList, ObservableDict, autorun


class TestObservable:
    def test_get_set(self):
        o = Observable(42)
        assert o.get() == 42
        o.set(100)
        assert o.get() == 100

    def test_dedup(self):
        """Setting the same value should not trigger observers."""
        o = Observable(42)
        log = []
        autorun(lambda: log.append(o.get()))
        assert log == [42]
        o.set(42)
        assert log == [42]  # no re-run

    def test_notifies_observers(self):
        o = Observable("hello")
        log = []
        autorun(lambda: log.append(o.get()))
        assert log == ["hello"]
        o.set("world")
        assert log == ["hello", "world"]

    def test_repr(self):
        o = Observable(5)
        assert "Observable(5)" in repr(o)


class TestObservableList:
    def test_basic_operations(self):
        lst = ObservableList([1, 2, 3])
        assert len(lst) == 3
        assert lst[0] == 1
        assert list(lst) == [1, 2, 3]
        assert 2 in lst
        assert bool(lst) is True

    def test_mutations_notify(self):
        lst = ObservableList([1, 2])
        log = []
        autorun(lambda: log.append(list(lst)))
        assert log == [[1, 2]]
        lst.append(3)
        assert log == [[1, 2], [1, 2, 3]]
        lst.pop()
        assert log == [[1, 2], [1, 2, 3], [1, 2]]

    def test_extend(self):
        lst = ObservableList()
        log = []
        autorun(lambda: log.append(list(lst)))
        lst.extend([1, 2, 3])
        assert log == [[], [1, 2, 3]]

    def test_insert_remove_clear(self):
        lst = ObservableList([1, 2, 3])
        lst.insert(1, 99)
        assert list(lst) == [1, 99, 2, 3]
        lst.remove(99)
        assert list(lst) == [1, 2, 3]
        lst.clear()
        assert list(lst) == []

    def test_setitem_delitem(self):
        lst = ObservableList([1, 2, 3])
        lst[1] = 20
        assert list(lst) == [1, 20, 3]
        del lst[0]
        assert list(lst) == [20, 3]


class TestObservableDict:
    def test_basic_operations(self):
        d = ObservableDict({"a": 1, "b": 2})
        assert d["a"] == 1
        assert d.get("c", 99) == 99
        assert "a" in d
        assert len(d) == 2
        assert set(d) == {"a", "b"}
        assert bool(d) is True

    def test_mutations_notify(self):
        d = ObservableDict({"a": 1})
        log = []
        autorun(lambda: log.append(dict(d.items())))
        assert log == [{"a": 1}]
        d["b"] = 2
        assert log == [{"a": 1}, {"a": 1, "b": 2}]

    def test_pop_del_clear(self):
        d = ObservableDict({"a": 1, "b": 2})
        result = d.pop("a")
        assert result == 1
        assert "a" not in d
        del d["b"]
        assert len(d) == 0
        d["x"] = 10
        d.clear()
        assert len(d) == 0

    def test_update(self):
        d = ObservableDict({"a": 1})
        d.update({"b": 2}, c=3)
        assert d["b"] == 2
        assert d["c"] == 3

    def test_setdefault(self):
        d = ObservableDict({"a": 1})
        assert d.setdefault("a", 99) == 1
        assert d.setdefault("b", 42) == 42
        assert d["b"] == 42

    def test_keys_values_items(self):
        d = ObservableDict({"a": 1, "b": 2})
        assert set(d.keys()) == {"a", "b"}
        assert set(d.values()) == {1, 2}
        assert set(d.items()) == {("a", 1), ("b", 2)}
