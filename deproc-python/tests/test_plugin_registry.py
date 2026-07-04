"""Tests for PluginRegistry."""
import pytest
from unittest.mock import MagicMock
from deproc.core.runtime.contracts import LanguagePlugin
from deproc.core.runtime.registries.plugin import PluginRegistry

def _make_plugin(
    language: str = "python",
    aliases: list[str] | None = None,
    file_extensions: list[str] | None = None,
) -> LanguagePlugin:
    return LanguagePlugin(
        language=language,
        aliases=aliases or [],
        file_extensions=file_extensions or [],
        linker=MagicMock(),
        resolver=MagicMock(),
        source_parser=MagicMock(),
        symbol_cache=MagicMock(),
        symbol_table_builder=MagicMock(),
    )

class TestPluginRegistry:
    def setup_method(self):
        self.registry = PluginRegistry()

    def test_register_and_get_by_language(self):
        plugin = _make_plugin(language="python", file_extensions=[".py"])
        self.registry.register(plugin)
        result = self.registry.get_plugin_by_language("python")
        assert result is plugin

    def test_register_and_get_by_extension(self):
        plugin = _make_plugin(language="python", file_extensions=[".py"])
        self.registry.register(plugin)
        result = self.registry.get_plugin_by_extension(".py")
        assert result is plugin

    def test_canonical_language_normalization(self):
        plugin = _make_plugin(language="Python")
        self.registry.register(plugin)
        result = self.registry.get_plugin_by_language("python")
        assert result is plugin

    def test_same_instance_returned(self):
        plugin = _make_plugin(language="python")
        self.registry.register(plugin)
        first = self.registry.get_plugin_by_language("python")
        second = self.registry.get_plugin_by_language("python")
        assert first is second is plugin

    def test_aliases_resolve_to_canonical_language(self):
        plugin = _make_plugin(language="cpp", aliases=["c++", "cplusplus"])
        self.registry.register(plugin)
        assert self.registry.get_plugin_by_language("c++") is plugin
        assert self.registry.get_plugin_by_language("CPlusPlus") is plugin

    def test_extension_from_alias_language(self):
        plugin = _make_plugin(language="cpp", aliases=["c++"], file_extensions=[".cpp"])
        self.registry.register(plugin)
        assert self.registry.get_plugin_by_extension(".cpp") is plugin

    def test_supported_languages_returns_sorted(self):
        js = _make_plugin(language="javascript")
        py = _make_plugin(language="python")
        self.registry.register(js)
        self.registry.register(py)
        assert self.registry.supported_languages() == ["javascript", "python"]

    def test_supported_file_extensions_returns_sorted(self):
        a = _make_plugin(language="a", file_extensions=[".a", ".aa"])
        b = _make_plugin(language="b", file_extensions=[".b"])
        self.registry.register(b)
        self.registry.register(a)
        assert self.registry.supported_file_extensions() == [".a", ".aa", ".b"]

    def test_get_plugin_by_language_raises_import_error(self):
        with pytest.raises(ImportError, match="not installed"):
            self.registry.get_plugin_by_language("nonexistent")

    def test_get_plugin_by_extension_raises_import_error(self):
        with pytest.raises(ImportError, match="No language plugin registered"):
            self.registry.get_plugin_by_extension(".xyz")

    def test_multiple_languages(self):
        py = _make_plugin(language="python", file_extensions=[".py"])
        js = _make_plugin(language="javascript", file_extensions=[".js"])
        self.registry.register(py)
        self.registry.register(js)
        assert self.registry.get_plugin_by_language("python") is py
        assert self.registry.get_plugin_by_language("javascript") is js
        assert self.registry.get_plugin_by_extension(".py") is py
        assert self.registry.get_plugin_by_extension(".js") is js

    def test_get_file_extensions_for_language(self):
        plugin = _make_plugin(language="c", aliases=["c"], file_extensions=[".c", ".h"])
        self.registry.register(plugin)
        exts = self.registry.get_file_extensions_for_language("c")
        assert exts == [".c", ".h"]
        exts2 = self.registry.get_file_extensions_for_language("C")
        assert exts2 == [".c", ".h"]

    def test_empty_registry_supported_language_names(self):
        assert self.registry.supported_languages() == []

    def test_empty_registry_supported_extensions(self):
        assert self.registry.supported_file_extensions() == []

    def test_normalize_empty_language_returns_empty(self):
        assert self.registry.normalize_language("") == ""
        assert self.registry.normalize_language("  ") == ""

    def test_normalize_empty_extension_returns_empty(self):
        assert self.registry.normalize_extension("") == ""
        assert self.registry.normalize_extension("  ") == ""

    def test_extension_normalization_adds_dot(self):
        plugin = _make_plugin(language="text", file_extensions=[".txt"])
        self.registry.register(plugin)
        result = self.registry.get_plugin_by_extension("txt")
        assert result is plugin

    def test_normalize_extension_untracked_returns_as_is(self):
        result = self.registry.normalize_extension("txt")
        assert result == ".txt"
