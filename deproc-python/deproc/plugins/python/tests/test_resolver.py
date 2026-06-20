"""Tests for Python symbol resolver."""

from unittest.mock import MagicMock
from deproc.core.context import Context
from deproc.core.interfaces.parser.models import (
    generate_id,
    SourceRange
)
from deproc.plugins.python.resolver.models import PythonResolverInput
from deproc.plugins.python.resolver.utils import (
    resolve_symbol,
    _extract_alias_ids
)
from deproc.plugins.python.parser.models import PythonImportAlias
from deproc.plugins.python.symbol_table_builder.models import (
    PythonSymbolTable,
    PythonModuleSymbolMap
)


class TestResolver:
    """Test symbol resolution."""

    def setup_method(self):
        """Set up mock context and dependencies."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}

    def test_extract_alias_ids_empty(self):
        """Extract from empty list."""
        alias_ids, non_alias_ids = _extract_alias_ids([], self.context)
        assert alias_ids == set()
        assert non_alias_ids == set()

    def test_extract_alias_ids_with_aliases(self):
        """Separate alias and non-alias symbols."""
        alias = PythonImportAlias(
            id="alias_1",
            name="MyImport",
            parent_id="import_stmt_1",
            alias="MyImportAlias",
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=1, end_col_offset=20)
        )
        self.context.entity_registry = {"alias_1": alias}

        alias_ids, non_alias_ids = _extract_alias_ids(["alias_1"], self.context)
        assert "alias_1" in alias_ids
        assert len(non_alias_ids) == 0

    def test_extract_mixed_ids(self):
        """Extract mixed alias and non-alias IDs."""
        alias = PythonImportAlias(
            id="alias_1",
            name="MyImport",
            parent_id="import_stmt_1",
            alias="MyImportAlias",
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=1, end_col_offset=20)
        )
        self.context.entity_registry = {
            "alias_1": alias,
            "class_1": {"type": "class"}  # Non-alias
        }

        alias_ids, non_alias_ids = _extract_alias_ids(["alias_1", "class_1"], self.context)
        assert "alias_1" in alias_ids
        assert "class_1" in non_alias_ids

    def test_resolve_symbol_not_found(self):
        """Resolve symbol not in table."""
        symbol_table = PythonSymbolTable(module_symbol_maps={})
        self.context.get_symbol_table.return_value = symbol_table
        self.context.get_symbol_cache.return_value = None

        data_in = PythonResolverInput(
            module_fqn="mymodule",
            symbol_name="MissingClass"
        )
        result = resolve_symbol(data_in, self.context)
        assert result == []

    def test_resolve_symbol_found(self):
        """Resolve symbol in table."""
        random_ids = {generate_id() for _ in range(2)}
        module_map = {
            "MyClass": random_ids
        }
        symbol_table = PythonSymbolTable(
            module_symbol_maps={"mymodule": module_map}
        )
        self.context.get_symbol_table.return_value = symbol_table
        self.context.get_symbol_cache.return_value = None
        self.context.entity_registry = {}

        data_in = PythonResolverInput(
            module_fqn="mymodule",
            symbol_name="MyClass"
        )
        result = resolve_symbol(data_in, self.context)

        id_1 = random_ids.pop()
        id_2 = random_ids.pop()
        assert id_1 in result
        assert id_2 in result