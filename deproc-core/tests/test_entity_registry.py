"""Tests for EntityRegistry."""

from dataclasses import dataclass

import pytest
from deproc.core.interfaces.parser.models import Entity, SemanticContainer, SymbolID
from deproc.core.runtime.registries.entity import EntityRegistry


@dataclass(kw_only=True)
class _FakeFqnEntity(Entity):
    fqn: str


@dataclass(kw_only=True)
class _FakeSemanticContainer(SemanticContainer):
    fqn: str
    items: list[SymbolID]

    @property
    def contribution_ids(self) -> list[SymbolID]:
        return self.items

    def _merge_contributions(self, other: SemanticContainer) -> None:
        assert isinstance(other, _FakeSemanticContainer)
        self.items = sorted(set(self.items) | set(other.items))


@dataclass(kw_only=True)
class _OtherFakeSemanticContainer(_FakeSemanticContainer):
    pass


class TestEntityRegistryValues:
    def test_empty_registry_values(self):
        registry = EntityRegistry()
        assert list(registry.values()) == []

    def test_values_after_add(self):
        registry = EntityRegistry()
        e1 = Entity(id="id_1")
        e2 = Entity(id="id_2")
        registry.add(e1)
        registry.add(e2)
        assert list(registry.values()) == [e1, e2]

    def test_values_after_add_all(self):
        registry = EntityRegistry()
        e1 = Entity(id="id_1")
        e2 = Entity(id="id_2")
        registry.add_all([e1, e2])
        assert list(registry.values()) == [e1, e2]


class TestEntityRegistryGet:
    def test_get_returns_entity(self):
        registry = EntityRegistry()
        e = Entity(id="id_1")
        registry.add(e)
        assert registry.get("id_1") is e

    def test_get_missing_returns_none(self):
        registry = EntityRegistry()
        assert registry.get("nonexistent") is None

    def test_get_missing_returns_default(self):
        registry = EntityRegistry()
        assert registry.get("nonexistent", "fallback") == "fallback"

    def test_get_with_none_default(self):
        registry = EntityRegistry()
        assert registry.get("nonexistent", None) is None

    def test_get_default_not_used_when_found(self):
        registry = EntityRegistry()
        e = Entity(id="id_1")
        registry.add(e)
        assert registry.get("id_1", "fallback") is e


class TestEntityRegistryContains:
    def test_contains_added(self):
        registry = EntityRegistry()
        e = Entity(id="id_1")
        registry.add(e)
        assert "id_1" in registry

    def test_not_contains_missing(self):
        registry = EntityRegistry()
        assert "nonexistent" not in registry


class TestEntityRegistryFqnMapping:
    def test_add_entity_with_fqn_updates_mapping(self):
        registry = EntityRegistry()
        e = _FakeFqnEntity(id="id_1", fqn="mymodule.MyClass")
        registry.add(e)
        assert registry.get_ids_by_fqn("mymodule.MyClass") == {"id_1"}

    def test_add_entity_without_fqn_does_not_update_mapping(self):
        registry = EntityRegistry()
        e = Entity(id="id_1")
        registry.add(e)
        assert registry.get_ids_by_fqn("anything") == set()

    def test_variable_binding_fqn_updates_mapping(self):
        registry = EntityRegistry()
        e = Entity(id="id_1")
        e.variable_binding = type("Binding", (), {"fqn": "pkg.Type.field"})()
        registry.add(e)
        assert registry.get_ids_by_fqn("pkg.Type.field") == {"id_1"}

    def test_replacing_entity_updates_fqn_mapping(self):
        registry = EntityRegistry()
        registry.add(_FakeFqnEntity(id="id_1", fqn="old.Name"))
        registry.add(_FakeFqnEntity(id="id_1", fqn="new.Name"))
        assert registry.get_ids_by_fqn("old.Name") == set()
        assert registry.get_ids_by_fqn("new.Name") == {"id_1"}

    def test_get_ids_by_fqn_returns_empty_for_missing(self):
        registry = EntityRegistry()
        assert registry.get_ids_by_fqn("nonexistent") == set()

    def test_get_ids_by_fqn_multiple_entities_same_fqn(self):
        registry = EntityRegistry()
        e1 = _FakeFqnEntity(id="id_1", fqn="mymodule.MyClass")
        e2 = _FakeFqnEntity(id="id_2", fqn="mymodule.MyClass")
        registry.add(e1)
        registry.add(e2)
        assert registry.get_ids_by_fqn("mymodule.MyClass") == {"id_1", "id_2"}

    def test_remove_entity_cleans_up_fqn_mapping(self):
        registry = EntityRegistry()
        e = _FakeFqnEntity(id="id_1", fqn="mymodule.MyClass")
        registry.add(e)
        registry.remove("id_1")
        assert registry.get_ids_by_fqn("mymodule.MyClass") == set()
        assert "id_1" not in registry

    def test_remove_entity_without_fqn_does_not_error(self):
        registry = EntityRegistry()
        e = Entity(id="id_1")
        registry.add(e)
        registry.remove("id_1")
        assert "id_1" not in registry


class TestSemanticContainerMerge:
    def test_add_does_not_silently_replace_semantic_container(self):
        registry = EntityRegistry()
        first = _FakeSemanticContainer(fqn="pkg", items=["a"])
        second = _FakeSemanticContainer(fqn="pkg", items=["b"])
        registry.add(first)

        with pytest.raises(ValueError, match="merge_semantic_container"):
            registry.add(second)

        assert registry.get(first.id) is first
        assert first.items == ["a"]

    def test_merge_semantic_container_unions_contributions(self):
        registry = EntityRegistry()
        first = _FakeSemanticContainer(fqn="pkg", items=["a"])
        second = _FakeSemanticContainer(fqn="pkg", items=["b", "a"])
        registry.add(first)

        merged = registry.merge_semantic_container(second)

        assert merged is first
        assert first.items == ["a", "b"]
        assert registry.get_ids_by_fqn("pkg") == {first.id}

    def test_registry_merge_uses_explicit_container_merge(self):
        first_registry = EntityRegistry()
        second_registry = EntityRegistry()
        first = _FakeSemanticContainer(fqn="pkg", items=["a"])
        second = _FakeSemanticContainer(fqn="pkg", items=["b"])
        first_registry.add(first)
        second_registry.add(second)

        first_registry.merge_from(second_registry)

        assert first_registry.get(first.id) is first
        assert first.items == ["a", "b"]

    def test_different_semantic_container_types_have_distinct_identity(self):
        registry = EntityRegistry()
        first = _FakeSemanticContainer(fqn="pkg", items=["a"])
        second = _OtherFakeSemanticContainer(fqn="pkg", items=["b"])

        assert first.id != second.id
        registry.merge_semantic_container(first)
        registry.merge_semantic_container(second)

        assert len(list(registry.values())) == 2
        assert registry.get_ids_by_fqn("pkg") == {first.id, second.id}
