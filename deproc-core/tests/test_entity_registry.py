"""Tests for EntityRegistry."""

from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.core.interfaces.parser.models import Entity

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
