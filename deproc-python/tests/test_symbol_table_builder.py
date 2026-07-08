"""Tests for Python symbol table builder."""

from deproc.core.context import Context
from deproc.plugins.python.symbol_table_builder.main import PythonSymbolTableBuilder
from deproc.plugins.python.symbol_table_builder.models import (
    PythonSymbolTable,
)
from deproc.plugins.python.parser import PythonSourceParser
from deproc.plugins.python.linker import PythonLinker
import tempfile

def _create_temp_file(content: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.py') as tmp:
        tmp.write(content)
        return tmp.name

class TestSymbolTableBuilder:
    def test_create_symbol_table(self):
        table = PythonSymbolTable(module_symbol_maps={})
        assert table.module_symbol_maps == {}

    def test_add_module_symbols(self):
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
        map1 = {"A": {"id_1"}}
        map2 = {"B": {"id_2"}}
        table = PythonSymbolTable(
            module_symbol_maps={
                "pkg.mod1": map1,
                "pkg.mod2": map2
            }
        )
        assert len(table.module_symbol_maps) == 2

class TestPythonSymbolTableBuilderBuild:
    def test_build_with_class_and_function(self):
        code = '''
class MyClass:
    pass

def my_func():
    pass
'''
        filepath = _create_temp_file(code)
        ctx = Context()
        ctx.set_language("python", [".py"])
        ctx.set_parser("python", PythonSourceParser())
        ctx.set_linker("python", PythonLinker())
        ctx.set_symbol_table_builder("python", PythonSymbolTableBuilder())

        parser = ctx.get_parser("python")
        sf = parser.parse_file(filepath, ctx)

        linker = ctx.get_linker("python")
        linker.link_files([sf], ctx)

        builder = ctx.get_symbol_table_builder("python")
        symbol_table = builder.build(ctx)

        assert len(symbol_table.module_symbol_maps) > 0
        for _, symbol_map in symbol_table.module_symbol_maps.items():
            assert "MyClass" in symbol_map
            assert "my_func" in symbol_map

    def test_build_with_imports(self):
        code = '''
import os
from typing import List
'''
        filepath = _create_temp_file(code)
        ctx = Context()
        ctx.set_language("python", [".py"])
        ctx.set_parser("python", PythonSourceParser())
        ctx.set_linker("python", PythonLinker())
        ctx.set_symbol_table_builder("python", PythonSymbolTableBuilder())

        parser = ctx.get_parser("python")
        sf = parser.parse_file(filepath, ctx)

        linker = ctx.get_linker("python")
        linker.link_files([sf], ctx)

        builder = ctx.get_symbol_table_builder("python")
        symbol_table = builder.build(ctx)

        assert len(symbol_table.module_symbol_maps) > 0
        for symbol_map in symbol_table.module_symbol_maps.values():
            assert "os" in symbol_map
            assert "List" in symbol_map
