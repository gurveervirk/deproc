"""Tests for Java symbol cache."""

from deproc.plugins.java.symbol_cache.main import JavaSymbolCache


class TestSymbolCache:
    def setup_method(self):
        self.cache = JavaSymbolCache()

    def test_set_and_get(self):
        self.cache.set("com.example.Foo", "List", {"id_1"}, {"id_2"}, {"id_3"})
        result = self.cache.get("com.example.Foo", "List")
        assert result == ({"id_1"}, {"id_2"}, {"id_3"})

    def test_get_missing(self):
        assert self.cache.get("missing", "symbol") is None

    def test_cache_language(self):
        assert self.cache.language == "java"

    def test_cache_multiple_entries(self):
        self.cache.set("cu_a", "sym1", {"a"}, set(), set())
        self.cache.set("cu_b", "sym2", {"b"}, set(), set())
        assert self.cache.get("cu_a", "sym1") == ({"a"}, set(), set())
        assert self.cache.get("cu_b", "sym2") == ({"b"}, set(), set())

    def test_input_lists_normalized_to_sets(self):
        self.cache.set("cu_a", "sym1", ["a", "b"], ["c"], ["d"])
        result = self.cache.get("cu_a", "sym1")
        assert result == ({"a", "b"}, {"c"}, {"d"})

    def test_reverse_index_tracked(self):
        self.cache.set("cu_a", "sym1", {"a"}, set(), set())
        self.cache.set("cu_a", "sym2", {"b"}, set(), set())
        self.cache.set("cu_b", "sym3", {"c"}, set(), set())
        assert self.cache.compilation_unit_to_cache_keys["cu_a"] == {
            ("cu_a", "sym1"),
            ("cu_a", "sym2"),
        }

    def test_clear_compilation_unit(self):
        self.cache.set("cu_a", "sym1", {"a"}, set(), set())
        self.cache.set("cu_a", "sym2", {"b"}, set(), set())
        self.cache.set("cu_b", "sym3", {"c"}, set(), set())
        self.cache.clear_compilation_unit("cu_a")
        assert self.cache.get("cu_a", "sym1") is None
        assert self.cache.get("cu_a", "sym2") is None
        assert self.cache.get("cu_b", "sym3") == ({"c"}, set(), set())
        assert "cu_a" not in self.cache.compilation_unit_to_cache_keys

    def test_clear_compilation_unit_idempotent(self):
        self.cache.clear_compilation_unit("nonexistent")

    def test_clear_removes_all(self):
        self.cache.set("cu_a", "sym1", {"a"}, set(), set())
        self.cache.set("cu_b", "sym2", {"b"}, set(), set())
        self.cache.clear()
        assert self.cache.get("cu_a", "sym1") is None
        assert self.cache.get("cu_b", "sym2") is None
        assert self.cache.compilation_unit_to_cache_keys == {}
