import pytest
from deproc.core.context import Context
from deproc.core.interfaces.symbol_table_builder.models import SymbolTable
from unittest.mock import MagicMock

class TestSetLanguage:
    def test_set_language_adds_to_selected(self):
        ctx = Context()
        ctx.set_language("python", [".py", ".pyi"], aliases=["py"])
        assert ctx.selected_languages == {"python"}
        assert ctx.selected_file_extensions == {".py", ".pyi"}

    def test_set_language_normalizes_extension(self):
        ctx = Context()
        ctx.set_language("python", ["py", "pyi"])
        assert ctx.selected_file_extensions == {".py", ".pyi"}

    def test_set_language_normalizes_language(self):
        ctx = Context()
        ctx.set_language("Python", [".py"])
        assert ctx.selected_languages == {"python"}

    def test_set_language_without_aliases(self):
        ctx = Context()
        ctx.set_language("python", [".py"])
        assert ctx.selected_languages == {"python"}

    def test_multiple_languages(self):
        ctx = Context()
        ctx.set_language("python", [".py"])
        ctx.set_language("javascript", [".js"])
        assert ctx.selected_languages == {"python", "javascript"}
        assert ctx.selected_file_extensions == {".py", ".js"}

class TestSelectLanguages:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py"], aliases=["py"])
        self.ctx.set_language("javascript", [".js"])

    def test_exclude_language(self):
        self.ctx.select_languages(["!python"])
        assert self.ctx.selected_languages == {"javascript"}

    def test_include_language(self):
        self.ctx.select_languages(["!python"])
        self.ctx.select_languages(["python"])
        assert self.ctx.selected_languages == {"python", "javascript"}

    def test_select_by_alias(self):
        self.ctx.select_languages(["!python"])
        self.ctx.select_languages(["py"])
        assert "python" in self.ctx.selected_languages

    def test_unknown_language_ignored(self):
        self.ctx.select_languages(["!python"])
        self.ctx.select_languages(["unknown"])
        assert self.ctx.selected_languages == {"javascript"}

class TestSelectFileExtensions:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py", ".pyi"])

    def test_exclude_extension(self):
        self.ctx.select_file_extensions(["!.py"])
        assert self.ctx.selected_file_extensions == {".pyi"}

    def test_include_extension(self):
        self.ctx.select_file_extensions(["!.py"])
        self.ctx.select_file_extensions([".py"])
        assert self.ctx.selected_file_extensions == {".py", ".pyi"}

    def test_unknown_extension_ignored(self):
        self.ctx.select_file_extensions(["!.py"])
        self.ctx.select_file_extensions([".unknown"])
        assert self.ctx.selected_file_extensions == {".pyi"}

class TestSetParser:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py"])

    def test_set_and_get_parser(self):
        self.ctx.set_parser("python", "fake_parser")
        assert self.ctx.get_parser("python") == "fake_parser"

    def test_has_parser(self):
        assert not self.ctx.has_parser("python")
        self.ctx.set_parser("python", "fake_parser")
        assert self.ctx.has_parser("python")

    def test_remove_parser(self):
        self.ctx.set_parser("python", "fake_parser")
        self.ctx.remove_parser("python")
        assert not self.ctx.has_parser("python")

    def test_set_parser_raises_for_unregistered_language(self):
        with pytest.raises(KeyError, match="not registered"):
            self.ctx.set_parser("unknown", "fake_parser")

    def test_get_parser_missing_language_logs_warning(self, caplog):
        caplog.set_level("WARNING")
        self.ctx.get_parser("unknown")
        assert "not registered" in caplog.text

    def test_has_parser_missing_language_logs_warning(self, caplog):
        caplog.set_level("WARNING")
        self.ctx.has_parser("unknown")
        assert "not registered" in caplog.text

class TestSetResolver:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py"])

    def test_set_and_get_resolver(self):
        self.ctx.set_resolver("python", "fake_resolver")
        assert self.ctx.get_resolver("python") == "fake_resolver"

    def test_has_resolver(self):
        assert not self.ctx.has_resolver("python")
        self.ctx.set_resolver("python", "fake_resolver")
        assert self.ctx.has_resolver("python")

    def test_remove_resolver(self):
        self.ctx.set_resolver("python", "fake_resolver")
        self.ctx.remove_resolver("python")
        assert not self.ctx.has_resolver("python")

    def test_set_resolver_raises_for_unregistered_language(self):
        with pytest.raises(KeyError, match="not registered"):
            self.ctx.set_resolver("unknown", "fake_resolver")

    def test_get_resolver_missing_language_logs_warning(self, caplog):
        caplog.set_level("WARNING")
        self.ctx.get_resolver("unknown")
        assert "not registered" in caplog.text

class TestSetLinker:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py"])

    def test_set_and_get_linker(self):
        self.ctx.set_linker("python", "fake_linker")
        assert self.ctx.get_linker("python") == "fake_linker"

    def test_has_linker(self):
        assert not self.ctx.has_linker("python")
        self.ctx.set_linker("python", "fake_linker")
        assert self.ctx.has_linker("python")

    def test_remove_linker(self):
        self.ctx.set_linker("python", "fake_linker")
        self.ctx.remove_linker("python")
        assert not self.ctx.has_linker("python")

    def test_set_linker_raises_for_unregistered_language(self):
        with pytest.raises(KeyError, match="not registered"):
            self.ctx.set_linker("unknown", "fake_linker")

    def test_get_linker_missing_language_logs_warning(self, caplog):
        caplog.set_level("WARNING")
        self.ctx.get_linker("unknown")
        assert "not registered" in caplog.text

class TestSetSymbolTableBuilder:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py"])

    def test_set_and_get_symbol_table_builder(self):
        self.ctx.set_symbol_table_builder("python", "fake_builder")
        assert self.ctx.get_symbol_table_builder("python") == "fake_builder"

    def test_has_symbol_table_builder(self):
        assert not self.ctx.has_symbol_table_builder("python")
        self.ctx.set_symbol_table_builder("python", "fake_builder")
        assert self.ctx.has_symbol_table_builder("python")

    def test_remove_symbol_table_builder(self):
        self.ctx.set_symbol_table_builder("python", "fake_builder")
        self.ctx.remove_symbol_table_builder("python")
        assert not self.ctx.has_symbol_table_builder("python")

    def test_set_symbol_table_builder_raises_for_unregistered_language(self):
        with pytest.raises(KeyError, match="not registered"):
            self.ctx.set_symbol_table_builder("unknown", "fake_builder")

class TestSetSymbolTable:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py"])
        self.symbol_table = SymbolTable(language="python")

    def test_set_and_get_symbol_table(self):
        self.ctx.set_symbol_table(self.symbol_table)
        assert self.ctx.get_symbol_table("python") is self.symbol_table

    def test_has_symbol_table(self):
        assert not self.ctx.has_symbol_table("python")
        self.ctx.set_symbol_table(self.symbol_table)
        assert self.ctx.has_symbol_table("python")

    def test_remove_symbol_table(self):
        self.ctx.set_symbol_table(self.symbol_table)
        self.ctx.remove_symbol_table("python")
        assert not self.ctx.has_symbol_table("python")

    def test_set_symbol_table_raises_for_unregistered_language(self):
        st = SymbolTable(language="unknown")
        with pytest.raises(KeyError, match="not registered"):
            self.ctx.set_symbol_table(st)

    def test_get_symbol_table_missing_language_logs_warning(self, caplog):
        caplog.set_level("WARNING")
        self.ctx.get_symbol_table("unknown")
        assert "not registered" in caplog.text

class TestSetSymbolCache:
    def setup_method(self):
        self.ctx = Context()
        self.ctx.set_language("python", [".py"])
        self.cache = MagicMock()
        self.cache.language = "python"

    def test_set_and_get_symbol_cache(self):
        self.ctx.set_symbol_cache(self.cache)
        assert self.ctx.get_symbol_cache("python") is self.cache

    def test_has_symbol_cache(self):
        assert not self.ctx.has_symbol_cache("python")
        self.ctx.set_symbol_cache(self.cache)
        assert self.ctx.has_symbol_cache("python")

    def test_remove_symbol_cache(self):
        self.ctx.set_symbol_cache(self.cache)
        self.ctx.remove_symbol_cache("python")
        assert not self.ctx.has_symbol_cache("python")

    def test_set_symbol_cache_raises_for_unregistered_language(self):
        cache = MagicMock()
        cache.language = "unknown"
        with pytest.raises(KeyError, match="not registered"):
            self.ctx.set_symbol_cache(cache)

    def test_get_symbol_cache_missing_language_logs_warning(self, caplog):
        caplog.set_level("WARNING")
        self.ctx.get_symbol_cache("unknown")
        assert "not registered" in caplog.text

class TestCopyFrom:
    def test_copy_preserves_language_config(self):
        ctx = Context()
        ctx.set_language("python", [".py"], aliases=["py"])
        ctx.set_parser("python", "fake_parser")
        copy = Context(copy_from=ctx)
        assert copy.selected_languages == {"python"}
        assert copy.selected_file_extensions == {".py"}
        assert copy.get_parser("python") == "fake_parser"

    def test_copy_is_independent(self):
        ctx = Context()
        ctx.set_language("python", [".py"])
        ctx.set_parser("python", "fake_parser")
        copy = Context(copy_from=ctx)
        copy.set_parser("python", "different_parser")
        assert ctx.get_parser("python") == "fake_parser"
        assert copy.get_parser("python") == "different_parser"

    def test_copy_by_default_empty(self):
        ctx = Context()
        assert ctx.selected_languages == set()
        assert ctx.selected_file_extensions == set()

class TestReset:
    def test_reset_restores_all_languages(self):
        ctx = Context()
        ctx.set_language("python", [".py"])
        ctx.set_language("javascript", [".js"])
        ctx.select_languages(["!python"])
        ctx.reset()
        assert ctx.selected_languages == {"python", "javascript"}

    def test_reset_restores_all_file_extensions(self):
        ctx = Context()
        ctx.set_language("python", [".py", ".pyi"])
        ctx.select_file_extensions(["!.py"])
        ctx.reset()
        assert ctx.selected_file_extensions == {".py", ".pyi"}

    def test_reset_skips_languages_when_flag_false(self):
        ctx = Context()
        ctx.set_language("python", [".py"])
        ctx.select_languages(["!python"])
        ctx.reset(include_languages=False)
        assert ctx.selected_languages == set()

    def test_reset_clears_symbol_tables(self):
        ctx = Context()
        ctx.set_language("python", [".py"])
        ctx.set_symbol_table(SymbolTable(language="python"))
        ctx.reset(include_languages=False, include_file_extensions=False)
        assert not ctx.has_symbol_table("python")

class TestEmptyContext:
    def test_empty_selected_languages(self):
        ctx = Context()
        assert ctx.selected_languages == set()

    def test_empty_selected_file_extensions(self):
        ctx = Context()
        assert ctx.selected_file_extensions == set()

    def test_get_parser_returns_none(self):
        ctx = Context()
        assert ctx.get_parser("anything") is None

    def test_has_parser_returns_false(self):
        ctx = Context()
        assert not ctx.has_parser("anything")

    def test_remove_parser_noop(self):
        ctx = Context()
        ctx.remove_parser("anything")

    def test_get_resolver_returns_none(self):
        ctx = Context()
        assert ctx.get_resolver("anything") is None

    def test_get_linker_returns_none(self):
        ctx = Context()
        assert ctx.get_linker("anything") is None

    def test_get_symbol_table_builder_returns_none(self):
        ctx = Context()
        assert ctx.get_symbol_table_builder("anything") is None

    def test_get_symbol_table_returns_none(self):
        ctx = Context()
        assert ctx.get_symbol_table("anything") is None

    def test_get_symbol_cache_returns_none(self):
        ctx = Context()
        assert ctx.get_symbol_cache("anything") is None
