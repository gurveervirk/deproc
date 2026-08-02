from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.core.runtime.registries.entity.utils import (
    entity_fqn,
    parent_chain,
    find_first_ancestor_of_type,
    classify_entity_scope,
)
from deproc.core.interfaces.parser.models import (
    Entity,
    SourceRange,
    FunctionLike,
    Signature,
)

class TestEntityFqn:
    def test_entity_with_fqn(self):
        e = FunctionLike(
            name="foo", fqn="pkg.mod.foo",
            docstring_range=None,
            source_range=SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=5),
            signature=Signature(
                signature_range=SourceRange(lineno=1, end_lineno=1, col_offset=5, end_col_offset=10),
                arguments_range=None,
                return_type_range=None,
            ),
        )
        assert entity_fqn(e) == "pkg.mod.foo"

    def test_entity_without_fqn(self):
        e = Entity()
        assert entity_fqn(e) is None

def _make_entity(id, parent_id=None, type=None):
    e = Entity()
    e.id = id
    e.parent_id = parent_id
    e.type = type
    return e

class TestParentChain:
    def test_single_entity(self):
        reg = EntityRegistry()
        e = _make_entity("a", type="MODULE")
        reg.add(e)
        assert parent_chain(reg, "a") == [e]

    def test_chain(self):
        reg = EntityRegistry()
        e1 = _make_entity("root", type="MODULE")
        e2 = _make_entity("cls", parent_id="root", type="CLASS")
        e3 = _make_entity("method", parent_id="cls", type="METHOD")
        reg.add_all([e1, e2, e3])
        chain = parent_chain(reg, "method")
        assert [e.id for e in chain] == ["method", "cls", "root"]

    def test_missing_entity_stops_chain(self):
        reg = EntityRegistry()
        e1 = _make_entity("a", parent_id="missing")
        reg.add(e1)
        chain = parent_chain(reg, "a")
        assert len(chain) == 1

    def test_cycle_stops(self):
        reg = EntityRegistry()
        e1 = _make_entity("a", parent_id="b")
        e2 = _make_entity("b", parent_id="a")
        reg.add_all([e1, e2])
        chain = parent_chain(reg, "a")
        assert [e.id for e in chain] == ["a", "b"]

class TestFindFirstAncestorOfType:
    def test_finds_ancestor(self):
        reg = EntityRegistry()
        e1 = _make_entity("mod", type="MODULE")
        e2 = _make_entity("cls", parent_id="mod", type="CLASS")
        e3 = _make_entity("method", parent_id="cls", type="METHOD")
        reg.add_all([e1, e2, e3])
        result = find_first_ancestor_of_type(reg, "method", {"MODULE"})
        assert result is not None
        assert result.id == "mod"

    def test_no_match(self):
        reg = EntityRegistry()
        e1 = _make_entity("cls", type="CLASS")
        e2 = _make_entity("method", parent_id="cls", type="METHOD")
        reg.add_all([e1, e2])
        result = find_first_ancestor_of_type(reg, "method", {"MODULE"})
        assert result is None

class TestClassifyEntityScope:
    def test_module_level(self):
        reg = EntityRegistry()
        e1 = _make_entity("mod", type="MODULE")
        e2 = _make_entity("cls", parent_id="mod", type="CLASS")
        reg.add_all([e1, e2])
        assert classify_entity_scope(reg, "cls") == "module_level"

    def test_conditional(self):
        reg = EntityRegistry()
        e1 = _make_entity("mod", type="MODULE")
        e2 = _make_entity("cflow", parent_id="mod", type="CONTROL_FLOW_BLOCK")
        e2.branch = "try"
        e3 = _make_entity("alias", parent_id="cflow", type="IMPORT_ALIAS")
        reg.add_all([e1, e2, e3])
        assert classify_entity_scope(reg, "alias") == "conditional:try"
