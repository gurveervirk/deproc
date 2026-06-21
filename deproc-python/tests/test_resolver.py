"""Tests for Python symbol resolver."""

from unittest.mock import MagicMock, Mock
from deproc.core.context import Context
from deproc.core.interfaces.parser.models import (
    generate_id,
    SourceRange
)
from deproc.plugins.python.resolver.utils import (
    resolve_symbol,
    resolve_alias_ids,
    resolve_alias,
    _extract_alias_ids,
    _get_target_module_fqn
)
from deproc.plugins.python.parser.models import (
    PythonImportAlias,
    PythonImportStatement
)
from deproc.plugins.python.linker.models import PythonModule
from deproc.plugins.python.symbol_table_builder.models import (
    PythonSymbolTable
)


class TestExtractAliasIds:
    """Test alias extraction from symbol IDs."""

    def setup_method(self):
        """Set up mock context."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}

    def test_extract_alias_ids_empty(self):
        """Extract from empty list."""
        alias_ids, non_alias_ids = _extract_alias_ids(set(), self.context)
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

        alias_ids, non_alias_ids = _extract_alias_ids({"alias_1"}, self.context)
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

        alias_ids, non_alias_ids = _extract_alias_ids({"alias_1", "class_1"}, self.context)
        assert "alias_1" in alias_ids
        assert "class_1" in non_alias_ids

    def test_extract_missing_symbol(self):
        """Handle missing symbol gracefully."""
        alias_ids, non_alias_ids = _extract_alias_ids({"missing_id"}, self.context)
        assert "missing_id" in non_alias_ids
        assert len(alias_ids) == 0


class TestResolveSymbol:
    """Test symbol resolution."""

    def setup_method(self):
        """Set up mock context and dependencies."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}

    def test_resolve_symbol_not_found(self):
        """Resolve symbol not in table."""
        symbol_table = PythonSymbolTable(module_symbol_maps={})
        self.context.get_symbol_table.return_value = symbol_table
        self.context.get_symbol_cache.return_value = None

        resolved, unresolved = resolve_symbol("mymodule", "MissingClass", self.context)
        assert resolved == set()
        assert unresolved == set()

    def test_resolve_symbol_found_direct(self):
        """Resolve symbol in table (direct, non-alias)."""
        class_id = generate_id()
        module_map = {
            "MyClass": [class_id]
        }
        symbol_table = PythonSymbolTable(
            module_symbol_maps={"mymodule": module_map}
        )
        self.context.get_symbol_table.return_value = symbol_table
        self.context.get_symbol_cache.return_value = None
        self.context.entity_registry = {}

        resolved, unresolved = resolve_symbol("mymodule", "MyClass", self.context)
        assert class_id in resolved
        assert len(unresolved) == 0

    def test_resolve_symbol_multiple_ids(self):
        """Resolve symbol with multiple direct IDs."""
        ids = {generate_id() for _ in range(3)}
        module_map = {"MyClass": ids}
        symbol_table = PythonSymbolTable(module_symbol_maps={"mymodule": module_map})
        self.context.get_symbol_table.return_value = symbol_table
        self.context.get_symbol_cache.return_value = None
        self.context.entity_registry = {}

        resolved, unresolved = resolve_symbol("mymodule", "MyClass", self.context)
        assert resolved == ids
        assert len(unresolved) == 0

    def test_resolve_symbol_no_symbol_table(self):
        """Handle missing symbol table."""
        self.context.get_symbol_table.return_value = None

        resolved, unresolved = resolve_symbol("mymodule", "MyClass", self.context)
        assert resolved == set()
        assert unresolved == set()


class TestResolveAliasIds:
    """Test resolution of multiple alias IDs."""

    def setup_method(self):
        """Set up mock context."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}
        self.cache = MagicMock()
        self.cache.get.return_value = None

    def test_resolve_alias_ids_empty(self):
        """Resolve empty alias set."""
        resolved, unresolved = resolve_alias_ids(set(), self.cache, self.context)
        assert resolved == set()
        assert unresolved == set()

    def test_resolve_alias_ids_unresolvable(self):
        """Unresolvable aliases become unresolved IDs."""
        alias_id = generate_id()
        alias = PythonImportAlias(
            id=alias_id,
            name="MissingImport",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="unknown_module",
            name_ids=[alias_id],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry = {
            alias_id: alias,
            "import_stmt_1": import_stmt
        }
        symbol_table = PythonSymbolTable(module_symbol_maps={})
        self.context.get_symbol_table.return_value = symbol_table

        resolved, unresolved = resolve_alias_ids({alias_id}, self.cache, self.context)
        assert len(resolved) == 0
        assert alias_id in unresolved

    def test_resolve_alias_ids_circular_reference(self):
        """Handle circular alias references gracefully."""
        alias_id_1 = generate_id()
        alias_id_2 = generate_id()
        
        alias_1 = PythonImportAlias(
            id=alias_id_1,
            name="SymbolB",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        alias_2 = PythonImportAlias(
            id=alias_id_2,
            name="SymbolA",
            parent_id="import_stmt_2",
            alias=None,
            source_range=SourceRange(lineno=2, end_lineno=2, col_offset=0, end_col_offset=10)
        )
        import_stmt_1 = PythonImportStatement(
            id="import_stmt_1",
            path="module_b",
            name_ids=[alias_id_1],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        import_stmt_2 = PythonImportStatement(
            id="import_stmt_2",
            path="module_a",
            name_ids=[alias_id_2],
            source_range=SourceRange(lineno=2, end_lineno=2, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        
        self.context.entity_registry = {
            alias_id_1: alias_1,
            alias_id_2: alias_2,
            "import_stmt_1": import_stmt_1,
            "import_stmt_2": import_stmt_2
        }
        
        # module_a has SymbolA -> alias_id_2, module_b has SymbolB -> alias_id_1
        symbol_table = PythonSymbolTable(
            module_symbol_maps={
                "module_a": {"SymbolA": [alias_id_2]},
                "module_b": {"SymbolB": [alias_id_1]}
            }
        )
        self.context.get_symbol_table.return_value = symbol_table

        resolved, unresolved = resolve_alias_ids({alias_id_1}, self.cache, self.context)
        # Should not hang, should handle gracefully by marking one as unresolved
        assert alias_id_1 in unresolved or len(resolved) == 0

    def test_resolve_alias_ids_mixed_resolved_unresolved(self):
        """Mix of resolvable and unresolvable aliases."""
        # Resolvable alias
        resolvable_alias_id = generate_id()
        resolvable_alias = PythonImportAlias(
            id=resolvable_alias_id,
            name="ValidSymbol",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        
        # Unresolvable alias
        unresolvable_alias_id = generate_id()
        unresolvable_alias = PythonImportAlias(
            id=unresolvable_alias_id,
            name="InvalidSymbol",
            parent_id="import_stmt_2",
            alias=None,
            source_range=SourceRange(lineno=2, end_lineno=2, col_offset=0, end_col_offset=10)
        )
        
        # Target symbol
        target_id = generate_id()
        
        import_stmt_1 = PythonImportStatement(
            id="import_stmt_1",
            path="valid_module",
            name_ids=[resolvable_alias_id],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        import_stmt_2 = PythonImportStatement(
            id="import_stmt_2",
            path="invalid_module",
            name_ids=[unresolvable_alias_id],
            source_range=SourceRange(lineno=2, end_lineno=2, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        
        self.context.entity_registry = {
            resolvable_alias_id: resolvable_alias,
            unresolvable_alias_id: unresolvable_alias,
            "import_stmt_1": import_stmt_1,
            "import_stmt_2": import_stmt_2
        }
        
        symbol_table = PythonSymbolTable(
            module_symbol_maps={
                "valid_module": {"ValidSymbol": [target_id]},
                # invalid_module not in table
            }
        )
        self.context.get_symbol_table.return_value = symbol_table

        resolved, unresolved = resolve_alias_ids(
            {resolvable_alias_id, unresolvable_alias_id},
            self.cache,
            self.context
        )
        assert target_id in resolved
        assert unresolvable_alias_id in unresolved


class TestResolveAlias:
    """Test individual alias resolution."""

    def setup_method(self):
        """Set up mock context."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}
        self.cache = MagicMock()
        self.cache.get.return_value = None

    def test_resolve_alias_target_not_in_table(self):
        """Unresolvable alias returns empty resolved and unresolved."""
        alias_id = generate_id()
        alias = PythonImportAlias(
            id=alias_id,
            name="MissingSymbol",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="unknown_module",
            name_ids=[alias_id],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry = {
            alias_id: alias,
            "import_stmt_1": import_stmt
        }
        symbol_table = PythonSymbolTable(module_symbol_maps={})
        self.context.get_symbol_table.return_value = symbol_table

        resolved, unresolved = resolve_alias(alias, self.cache, self.context)
        assert len(resolved) == 0
        assert len(unresolved) == 0

    def test_resolve_alias_target_module_not_found(self):
        """Missing target module returns empty."""
        alias_id = generate_id()
        alias = PythonImportAlias(
            id=alias_id,
            name="SomeSymbol",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="nonexistent",
            name_ids=[alias_id],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry = {
            alias_id: alias,
            "import_stmt_1": import_stmt
        }
        symbol_table = PythonSymbolTable(module_symbol_maps={})
        self.context.get_symbol_table.return_value = symbol_table

        resolved, unresolved = resolve_alias(alias, self.cache, self.context)
        assert len(resolved) == 0
        assert len(unresolved) == 0

    def test_resolve_alias_with_cache_hit(self):
        """Cache hit returns cached result."""
        alias_id = generate_id()
        alias = PythonImportAlias(
            id=alias_id,
            name="SomeSymbol",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="x.y.z",
            name_ids=[alias_id],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry = {
            alias_id: alias,
            "import_stmt_1": import_stmt
        }
        cached_result = ({alias_id}, set())
        self.cache.get.return_value = cached_result

        resolved, unresolved = resolve_alias(alias, self.cache, self.context)
        assert resolved == cached_result[0]
        assert unresolved == cached_result[1]
        self.cache.get.assert_called()

    def test_resolve_alias_direct_symbol(self):
        """Resolve alias to direct symbol (non-alias)."""
        alias_id = generate_id()
        target_id = generate_id()
        alias = PythonImportAlias(
            id=alias_id,
            name="DirectSymbol",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="some_module",
            name_ids=[alias_id],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry = {
            alias_id: alias,
            "import_stmt_1": import_stmt,
            target_id: {"type": "class"}  # Non-alias target
        }
        symbol_table = PythonSymbolTable(
            module_symbol_maps={
                "some_module": {"DirectSymbol": [target_id]}
            }
        )
        self.context.get_symbol_table.return_value = symbol_table

        resolved, unresolved = resolve_alias(alias, self.cache, self.context)
        assert target_id in resolved
        assert len(unresolved) == 0


class TestGetTargetModuleFqn:
    """Test module FQN resolution for imports."""

    def setup_method(self):
        """Set up mock context."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}

    def test_get_target_module_absolute_path(self):
        """Resolve absolute import path."""
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="some.module.path",
            name_ids=[],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry["import_stmt_1"] = import_stmt

        result = _get_target_module_fqn("import_stmt_1", self.context)
        assert result == "some.module.path"

    def test_get_target_module_relative_import(self):
        """Resolve relative import from parent module."""
        parent_module = PythonModule(
            id="module_1",
            fqn="package.subpackage.module",
            path="/path/to/module.py",
            docstring_range=None,
            source=""
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path=".sibling",
            name_ids=[],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry = {
            "import_stmt_1": import_stmt,
            "parent_1": parent_module
        }
        
        # Mock _get_module to return parent
        import_stmt.parent_id = "parent_1"

        result = _get_target_module_fqn("import_stmt_1", self.context)
        # Relative import should resolve relative to parent
        assert result is not None

    def test_get_target_module_missing_import_stmt(self):
        """Handle missing import statement."""
        result = _get_target_module_fqn("nonexistent", self.context)
        assert result is None