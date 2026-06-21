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
