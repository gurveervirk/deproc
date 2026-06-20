"""Tests for Python symbol table builder."""

from deproc.plugins.python.symbol_table_builder.models import (
    PythonSymbolTable,
    PythonModuleSymbolMap
)


class TestSymbolTableBuilder:
    """Test symbol table construction."""

    def test_create_symbol_table(self):
        """Create empty symbol table."""
        table = PythonSymbolTable(module_symbol_maps={})
        assert table.module_symbol_maps == {}

    def test_add_module_symbols(self):
        """Add symbols for a module."""
        module_map = {
            "MyClass": {"id_1"},
            "my_func": {"id_2"}
        }
        table = PythonSymbolTable(
            module_symbol_maps={"mymodule": module_map}
        )
        assert "mymodule" in table.module_symbol_maps
        assert table.module_symbol_maps["mymodule"]["MyClass"] == {"id_1"}

    def test_multiple_modules(self):
        """Symbol table with multiple modules."""
        map1 = {
            "A": {"id_1"}
        }
        map2 = {
            "B": {"id_2"}
        }
        table = PythonSymbolTable(
            module_symbol_maps={
                "pkg.mod1": map1,
                "pkg.mod2": map2
            }
        )
        assert len(table.module_symbol_maps) == 2
