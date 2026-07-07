"""Tests for Python symbol cache."""

from deproc.plugins.python.symbol_cache.main import PythonSymbolCache


class TestSymbolCache:
    """Test symbol caching."""

    def setup_method(self):
        """Create fresh cache."""
        self.cache = PythonSymbolCache()

    def test_set_and_get(self):
        """Store and retrieve cached symbol."""
        module_fqn = "my_module"
        symbol_name = "my_symbol"
        resolved_ids = ["id_1", "id_2"]
        unresolved_ids = ["id_3"]
        self.cache.set(module_fqn, symbol_name, resolved_ids, unresolved_ids)
        result = self.cache.get(module_fqn, symbol_name)
        assert result == (resolved_ids, unresolved_ids)

    def test_get_missing(self):
        """Get non-existent key."""
        result = self.cache.get("missing", "symbol")
        assert result is None

    def test_cache_language(self):
        """Cache tracks language."""
        assert self.cache.language == "python"

    def test_cache_multiple_entries(self):
        """Store multiple cache entries."""
        self.cache.set("mod1", "sym1", ["a"], [])
        self.cache.set("mod2", "sym2", ["b"], [])
        assert self.cache.get("mod1", "sym1") == (["a"], [])
        assert self.cache.get("mod2", "sym2") == (["b"], [])

    def test_add_cache_keys_for_module(self):
        self.cache.add_cache_keys_for_module("mod_a", {("mod_b", "sym"), ("mod_a", "sym")})
        assert self.cache.get_cache_keys_for_module("mod_a") == {("mod_b", "sym"), ("mod_a", "sym")}

    def test_get_cache_keys_for_module_empty(self):
        assert self.cache.get_cache_keys_for_module("missing") == set()
    
    def test_add_modules_for_cache_key(self):
        self.cache.add_modules_for_cache_key(("mod_a", "sym"), {"mod_a", "mod_b"})
        assert self.cache.get_modules_for_cache_key(("mod_a", "sym")) == {"mod_a", "mod_b"}

    def test_get_modules_for_cache_key_empty(self):
        assert self.cache.get_modules_for_cache_key(("missing", "sym")) == set()

    def test_bidirectional_consistency(self):
        self.cache.add_cache_keys_for_module("mod_a", {("mod_a", "sym1")})
        self.cache.add_modules_for_cache_key(("mod_b", "sym2"), {"mod_b"})
        assert ("mod_a", "sym1") in self.cache.get_cache_keys_for_module("mod_a")
        assert "mod_a" in self.cache.get_modules_for_cache_key(("mod_a", "sym1"))
        assert "mod_b" in self.cache.get_modules_for_cache_key(("mod_b", "sym2"))
        assert ("mod_b", "sym2") in self.cache.get_cache_keys_for_module("mod_b")

    def test_clear_module_removes_cache_and_reverse_map(self):
        self.cache.set("mod_a", "sym1", ["id1"], [])
        self.cache.set("mod_b", "sym2", ["id2"], [])
        self.cache.add_cache_keys_for_module("mod_a", {("mod_a", "sym1")})
        self.cache.add_cache_keys_for_module("mod_b", {("mod_b", "sym2")})
        self.cache.clear_module("mod_a")
        assert self.cache.get("mod_a", "sym1") is None
        assert self.cache.get_cache_keys_for_module("mod_a") == set()
        assert self.cache.get_modules_for_cache_key(("mod_a", "sym1")) == set()
        assert self.cache.get("mod_b", "sym2") == (["id2"], [])
        assert self.cache.get_cache_keys_for_module("mod_b") == {("mod_b", "sym2")}

    def test_clear_module_idempotent(self):
        self.cache.clear_module("nonexistent")

    def test_clear_clears_all_maps(self):
        self.cache.set("mod_a", "sym1", ["id1"], [])
        self.cache.add_cache_keys_for_module("mod_a", {("mod_a", "sym1")})
        self.cache.add_modules_for_cache_key(("mod_b", "sym2"), {"mod_b"})
        self.cache.clear()
        assert self.cache.get("mod_a", "sym1") is None
        assert self.cache.get_cache_keys_for_module("mod_a") == set()
        assert self.cache.get_modules_for_cache_key(("mod_b", "sym2")) == set()
