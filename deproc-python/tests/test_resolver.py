"""Tests for Python symbol resolver."""

from dataclasses import dataclass
from unittest.mock import MagicMock, Mock
from deproc.core.context import Context
from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.core.interfaces.parser.models import (
    Entity,
    generate_id,
    SourceRange
)
from deproc.plugins.python.resolver.main import PythonResolver
from deproc.plugins.python.parser.models import (
    PythonImportAlias,
    PythonImportStatement,
    PythonModule,
)
from deproc.plugins.python.symbol_cache import PythonSymbolCache


@dataclass(kw_only=True)
class _FakeFqnEntity(Entity):
    fqn: str


class TestExtractAliasIds:
    def setup_method(self):
        self.resolver = PythonResolver()
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = EntityRegistry()

    def test_extract_alias_ids_empty(self):
        alias_ids, non_alias_ids = self.resolver._extract_alias_ids(set(), self.context)
        assert alias_ids == set()
        assert non_alias_ids == set()

    def test_extract_alias_ids_with_aliases(self):
        alias = PythonImportAlias(
            id="alias_1",
            name="MyImport",
            parent_id="import_stmt_1",
            alias="MyImportAlias",
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=1, end_col_offset=20)
        )
        self.context.entity_registry.add(alias)

        alias_ids, non_alias_ids = self.resolver._extract_alias_ids({"alias_1"}, self.context)
        assert "alias_1" in alias_ids
        assert len(non_alias_ids) == 0

    def test_extract_mixed_ids(self):
        alias = PythonImportAlias(
            id="alias_1",
            name="MyImport",
            parent_id="import_stmt_1",
            alias="MyImportAlias",
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=1, end_col_offset=20)
        )
        self.context.entity_registry.add(alias)
        self.context.entity_registry.entities["class_1"] = Mock()

        alias_ids, non_alias_ids = self.resolver._extract_alias_ids({"alias_1", "class_1"}, self.context)
        assert "alias_1" in alias_ids
        assert "class_1" in non_alias_ids

    def test_extract_missing_symbol(self):
        alias_ids, non_alias_ids = self.resolver._extract_alias_ids({"missing_id"}, self.context)
        assert "missing_id" in non_alias_ids
        assert len(alias_ids) == 0

class TestResolveSymbol:
    def setup_method(self):
        self.resolver = PythonResolver()
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = EntityRegistry()
        self.context.get_symbol_cache.return_value = None

    def test_resolve_symbol_not_found(self):
        resolved, unresolved = self.resolver.resolve_symbol("mymodule", "MissingClass", self.context)
        assert resolved == set()
        assert unresolved == set()

    def test_resolve_symbol_found_direct(self):
        class_id = generate_id()
        entity = _FakeFqnEntity(id=class_id, fqn="mymodule.MyClass")
        self.context.entity_registry.add(entity)

        resolved, unresolved = self.resolver.resolve_symbol("mymodule", "MyClass", self.context)
        assert class_id in resolved
        assert len(unresolved) == 0

    def test_resolve_symbol_multiple_ids(self):
        ids = {generate_id() for _ in range(3)}
        for id_ in ids:
            entity = _FakeFqnEntity(id=id_, fqn="mymodule.MyClass")
            self.context.entity_registry.add(entity)

        resolved, unresolved = self.resolver.resolve_symbol("mymodule", "MyClass", self.context)
        assert resolved == ids
        assert len(unresolved) == 0

class TestResolveAliasIds:
    def setup_method(self):
        self.resolver = PythonResolver()
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = EntityRegistry()
        self.context.get_symbol_cache.return_value = None

    def test_resolve_alias_ids_empty(self):
        resolved, unresolved = self.resolver.resolve_alias_ids(set(), self.context)
        assert resolved == set()
        assert unresolved == set()

    def test_resolve_alias_ids_unresolvable(self):
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
        self.context.entity_registry.add(alias)
        self.context.entity_registry.add(import_stmt)

        resolved, unresolved = self.resolver.resolve_alias_ids({alias_id}, self.context)
        assert len(resolved) == 0
        assert alias_id in unresolved

    def test_resolve_alias_ids_circular_reference(self):
        alias_id_1 = generate_id()
        alias_id_2 = generate_id()

        alias_1 = PythonImportAlias(
            id=alias_id_1,
            name="SymbolB",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10),
            fqn="module_b.SymbolB",
        )
        alias_2 = PythonImportAlias(
            id=alias_id_2,
            name="SymbolA",
            parent_id="import_stmt_2",
            alias=None,
            source_range=SourceRange(lineno=2, end_lineno=2, col_offset=0, end_col_offset=10),
            fqn="module_a.SymbolA",
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

        self.context.entity_registry.add(alias_1)
        self.context.entity_registry.add(alias_2)
        self.context.entity_registry.add(import_stmt_1)
        self.context.entity_registry.add(import_stmt_2)

        resolved, unresolved = self.resolver.resolve_alias_ids({alias_id_1}, self.context)
        assert alias_id_1 in unresolved or len(resolved) == 0

    def test_resolve_alias_ids_mixed_resolved_unresolved(self):
        resolvable_alias_id = generate_id()
        unresolvable_alias_id = generate_id()
        target_id = generate_id()

        resolvable_alias = PythonImportAlias(
            id=resolvable_alias_id,
            name="ValidSymbol",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10)
        )
        unresolvable_alias = PythonImportAlias(
            id=unresolvable_alias_id,
            name="InvalidSymbol",
            parent_id="import_stmt_2",
            alias=None,
            source_range=SourceRange(lineno=2, end_lineno=2, col_offset=0, end_col_offset=10)
        )
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

        target_entity = _FakeFqnEntity(id=target_id, fqn="valid_module.ValidSymbol")

        self.context.entity_registry.add(resolvable_alias)
        self.context.entity_registry.add(unresolvable_alias)
        self.context.entity_registry.add(import_stmt_1)
        self.context.entity_registry.add(import_stmt_2)
        self.context.entity_registry.add(target_entity)

        resolved, unresolved = self.resolver.resolve_alias_ids(
            {resolvable_alias_id, unresolvable_alias_id},
            self.context
        )
        assert target_id in resolved
        assert unresolvable_alias_id in unresolved

class TestResolveAlias:
    def setup_method(self):
        self.resolver = PythonResolver()
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = EntityRegistry()
        self.context.get_symbol_cache.return_value = None

    def test_resolve_alias_target_not_in_table(self):
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
        self.context.entity_registry.add(alias)
        self.context.entity_registry.add(import_stmt)

        resolved, unresolved = self.resolver.resolve_alias(alias, self.context)
        assert len(resolved) == 0
        assert len(unresolved) == 0

    def test_resolve_alias_target_module_not_found(self):
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
        self.context.entity_registry.add(alias)
        self.context.entity_registry.add(import_stmt)

        resolved, unresolved = self.resolver.resolve_alias(alias, self.context)
        assert len(resolved) == 0
        assert len(unresolved) == 0

    def test_resolve_alias_with_cache_hit(self):
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
        self.context.entity_registry.add(alias)
        self.context.entity_registry.add(import_stmt)
        cached_result = ({alias_id}, set())
        cache_mock = MagicMock()
        self.context.get_symbol_cache.return_value = cache_mock
        cache_mock.get.return_value = cached_result

        resolved, unresolved = self.resolver.resolve_alias(alias, self.context)
        assert resolved == cached_result[0]
        assert unresolved == cached_result[1]
        self.context.get_symbol_cache.return_value.get.assert_called()

    def test_resolve_alias_direct_symbol(self):
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
        target_entity = _FakeFqnEntity(id=target_id, fqn="some_module.DirectSymbol")
        self.context.entity_registry.add(alias)
        self.context.entity_registry.add(import_stmt)
        self.context.entity_registry.add(target_entity)

        resolved, unresolved = self.resolver.resolve_alias(alias, self.context)
        assert target_id in resolved
        assert len(unresolved) == 0

class TestGetTargetModuleFqn:
    def setup_method(self):
        self.resolver = PythonResolver()
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = EntityRegistry()

    def test_get_target_module_absolute_path(self):
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="some.module.path",
            name_ids=[],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry.add(import_stmt)

        result = self.resolver._get_target_module_fqn("import_stmt_1", self.context)
        assert result == "some.module.path"

    def _setup_relative_import(self, path: str, parent_fqn: str, module_path: str = "/path/to/module.py") -> PythonImportStatement:
        parent_module = PythonModule(
            id="module_1",
            fqn=parent_fqn,
            path=module_path,
            docstring_range=None,
            source=""
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path=path,
            name_ids=[],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        self.context.entity_registry.add(import_stmt)
        self.context.entity_registry.add(parent_module)
        import_stmt.parent_id = "module_1"
        return import_stmt

    def test_relative_import_single_dot(self):
        self._setup_relative_import(".sibling", "package.subpackage.module")
        result = self.resolver._get_target_module_fqn("import_stmt_1", self.context)
        assert result == "package.subpackage.sibling"

    def test_relative_import_single_dot_nested(self):
        self._setup_relative_import(".subpkg.module", "package.subpackage.module")
        result = self.resolver._get_target_module_fqn("import_stmt_1", self.context)
        assert result == "package.subpackage.subpkg.module"

    def test_relative_import_double_dot(self):
        self._setup_relative_import("..sibling", "package.subpackage.module")
        result = self.resolver._get_target_module_fqn("import_stmt_1", self.context)
        assert result == "package.sibling"

    def test_relative_import_triple_dot(self):
        self._setup_relative_import("...sibling", "package.subpackage.module")
        result = self.resolver._get_target_module_fqn("import_stmt_1", self.context)
        assert result == "sibling"

    def test_relative_import_top_level_single_dot(self):
        self._setup_relative_import(".module", "package", module_path="/path/to/__init__.py")
        result = self.resolver._get_target_module_fqn("import_stmt_1", self.context)
        assert result == "package.module"

    def test_relative_import_top_level_double_dot(self):
        self._setup_relative_import("..other", "package.subpackage")
        result = self.resolver._get_target_module_fqn("import_stmt_1", self.context)
        assert result == "other"

    def test_get_target_module_missing_import_stmt(self):
        result = self.resolver._get_target_module_fqn("nonexistent", self.context)
        assert result is None

class TestResolveSymbolWithCache:
    def setup_method(self):
        self.resolver = PythonResolver()
        self.cache = PythonSymbolCache()
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = EntityRegistry()
        self.context.get_symbol_cache.return_value = self.cache

    def test_resolve_symbol_populates_cache_key_maps(self):
        class_id = generate_id()
        entity = _FakeFqnEntity(id=class_id, fqn="mymodule.MyClass")
        self.context.entity_registry.add(entity)

        resolved, _ = self.resolver.resolve_symbol("mymodule", "MyClass", self.context)
        assert self.cache.get_cache_keys_for_module("mymodule") == {("mymodule", "MyClass")}
        assert class_id in resolved

    def test_clear_module_via_cache_after_resolve(self):
        class_id = generate_id()
        entity = _FakeFqnEntity(id=class_id, fqn="mymodule.MyClass")
        self.context.entity_registry.add(entity)

        self.resolver.resolve_symbol("mymodule", "MyClass", self.context)
        self.cache.clear_module("mymodule")
        assert self.cache.get("mymodule", "MyClass") is None
        assert self.cache.get_cache_keys_for_module("mymodule") == set()

    def test_resolve_symbol_cached_result_preserves_other_entries(self):
        class_id = generate_id()
        entity = _FakeFqnEntity(id=class_id, fqn="mymodule.MyClass")
        self.context.entity_registry.add(entity)

        other_id = generate_id()
        other_entity = _FakeFqnEntity(id=other_id, fqn="other.Other")
        self.context.entity_registry.add(other_entity)

        self.resolver.resolve_symbol("mymodule", "MyClass", self.context)
        self.resolver.resolve_symbol("other", "Other", self.context)
        self.cache.clear_module("mymodule")
        assert self.cache.get("mymodule", "MyClass") is None
        assert self.cache.get("other", "Other") is not None
        assert self.cache.get_cache_keys_for_module("other") == {("other", "Other")}

    def test_resolve_symbol_alias_populates_transitive_maps(self):
        target_id = generate_id()
        alias_id = generate_id()
        alias = PythonImportAlias(
            id=alias_id,
            name="AliasedClass",
            parent_id="import_stmt_1",
            alias=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=10),
            fqn="source_module.AliasedClass",
        )
        import_stmt = PythonImportStatement(
            id="import_stmt_1",
            path="target_module",
            name_ids=[alias_id],
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20),
            type="generic_import"
        )
        target_entity = _FakeFqnEntity(id=target_id, fqn="target_module.AliasedClass")

        self.context.entity_registry.add(alias)
        self.context.entity_registry.add(import_stmt)
        self.context.entity_registry.add(target_entity)

        self.resolver.resolve_symbol("source_module", "AliasedClass", self.context)
        source_keys = self.cache.get_cache_keys_for_module("source_module")
        target_keys = self.cache.get_cache_keys_for_module("target_module")
        assert ("source_module", "AliasedClass") in source_keys
        assert ("target_module", "AliasedClass") in source_keys
        assert ("source_module", "AliasedClass") in target_keys
        assert ("target_module", "AliasedClass") in target_keys
