"""Tests for deterministic entity ID generation."""
from dataclasses import dataclass
from uuid import uuid4
from deproc.core.interfaces.parser.models import (
    Entity,
    ImportStatement,
    Node,
    SourceFile,
    SourceRange,
    SimpleBinding,
    VariableDeclaration,
)

_PARENT = uuid4().hex
_OTHER_PARENT = uuid4().hex

@dataclass(kw_only=True)
class _EntityWithSource(Entity):
    source_range: SourceRange

class TestEntityDeterministicId:
    def test_same_parent_and_source_range_produces_same_id(self):
        sr = SourceRange(lineno=10, end_lineno=20, col_offset=1, end_col_offset=30)
        e1 = _EntityWithSource(parent_id=_PARENT, source_range=sr)
        e2 = _EntityWithSource(parent_id=_PARENT, source_range=sr)
        assert e1.id == e2.id

    def test_different_parent_id_produces_different_id(self):
        sr = SourceRange(lineno=10, end_lineno=20, col_offset=1, end_col_offset=30)
        e1 = _EntityWithSource(parent_id=_PARENT, source_range=sr)
        e2 = _EntityWithSource(parent_id=_OTHER_PARENT, source_range=sr)
        assert e1.id != e2.id

    def test_different_source_range_produces_different_id(self):
        sr1 = SourceRange(lineno=1, end_lineno=5, col_offset=0, end_col_offset=10)
        sr2 = SourceRange(lineno=2, end_lineno=5, col_offset=0, end_col_offset=10)
        e1 = _EntityWithSource(parent_id=_PARENT, source_range=sr1)
        e2 = _EntityWithSource(parent_id=_PARENT, source_range=sr2)
        assert e1.id != e2.id

    def test_different_subclass_types_produce_different_ids(self):
        sr = SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=5)

        @dataclass(kw_only=True)
        class SubA(Entity):
            source_range: SourceRange

        @dataclass(kw_only=True)
        class SubB(Entity):
            source_range: SourceRange

        a = SubA(parent_id=_PARENT, source_range=sr)
        b = SubB(parent_id=_PARENT, source_range=sr)
        assert a.id != b.id

    def test_entity_without_parent_id_is_not_deterministic(self):
        e1 = _EntityWithSource(
            parent_id=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=5),
        )
        e2 = _EntityWithSource(
            parent_id=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=5),
        )
        assert e1.id != e2.id

    def test_entity_without_source_range_is_not_deterministic(self):
        e1 = Entity(parent_id=_PARENT)
        e2 = Entity(parent_id=_PARENT)
        assert e1.id != e2.id

    def test_explicit_id_is_preserved(self):
        e = Entity(id="my-explicit-id")
        assert e.id == "my-explicit-id"

    def test_explicit_id_skips_computation(self):
        sr = SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=5)
        e = _EntityWithSource(id="explicit", parent_id=_PARENT, source_range=sr)
        assert e.id == "explicit"

class TestNodeDeterministicId:
    def test_same_path_produces_same_id(self):
        n1 = Node(path="src/main.py")
        n2 = Node(path="src/main.py")
        assert n1.id == n2.id

    def test_different_path_produces_different_id(self):
        n1 = Node(path="src/main.py")
        n2 = Node(path="src/utils.py")
        assert n1.id != n2.id

    def test_node_id_is_32_hex_chars(self):
        n = Node(path="src/main.py")
        assert isinstance(n.id, str)
        assert len(n.id) == 32

    def test_source_file_id_is_deterministic(self):
        sf1 = SourceFile(path="foo/bar.py", docstring_range=None, source="")
        sf2 = SourceFile(path="foo/bar.py", docstring_range=None, source="")
        assert sf1.id == sf2.id

    def test_source_file_with_different_path_has_different_id(self):
        sf1 = SourceFile(path="foo/bar.py", docstring_range=None, source="")
        sf2 = SourceFile(path="foo/baz.py", docstring_range=None, source="")
        assert sf1.id != sf2.id

    def test_node_uses_path_not_parent_id(self):
        @dataclass(kw_only=True)
        class NodeSubclass(Node):
            source_range: SourceRange

        sr = SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=5)
        n1 = NodeSubclass(path="foo.py", parent_id=_PARENT, source_range=sr)
        n2 = NodeSubclass(path="foo.py", parent_id=_OTHER_PARENT, source_range=sr)
        assert n1.id == n2.id

class TestConcreteSubclassDeterminism:
    def test_variable_declaration_with_parent_and_source_is_deterministic(self):
        sr = SourceRange(lineno=5, end_lineno=5, col_offset=0, end_col_offset=10)
        binding = SimpleBinding(name="x", fqn="mod.x")
        v1 = VariableDeclaration(
            parent_id=_PARENT,
            source_range=sr,
            variable_binding=binding,
            value_range=None,
            type_annotation=None,
        )
        v2 = VariableDeclaration(
            parent_id=_PARENT,
            source_range=sr,
            variable_binding=binding,
            value_range=None,
            type_annotation=None,
        )
        assert v1.id == v2.id

    def test_import_statement_with_parent_and_source_is_deterministic(self):
        sr = SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=20)
        i1 = ImportStatement(type="from_import", parent_id=_PARENT, source_range=sr)
        i2 = ImportStatement(type="from_import", parent_id=_PARENT, source_range=sr)
        assert i1.id == i2.id
