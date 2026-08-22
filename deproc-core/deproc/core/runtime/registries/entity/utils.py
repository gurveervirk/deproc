from __future__ import annotations

from typing import TYPE_CHECKING

from . import EntityRegistry

if TYPE_CHECKING:
    from ....interfaces.parser.models import Entity, SymbolID


def entity_fqn(entity: Entity) -> str | None:
    fqn = getattr(entity, "fqn", None)
    if fqn:
        return fqn
    vb = getattr(entity, "variable_binding", None)
    if vb:
        return getattr(vb, "fqn", None)
    return None


def parent_chain(registry: EntityRegistry, entity_id: SymbolID) -> list[Entity]:
    chain: list[Entity] = []
    current_id = entity_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        entity = registry.get(current_id)
        if not entity:
            break
        chain.append(entity)
        current_id = getattr(entity, "parent_id", None)
    return chain


def find_first_ancestor_of_type(
    registry: EntityRegistry, entity_id: SymbolID, types: set[str]
) -> Entity | None:
    current_id = entity_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        entity = registry.get(current_id)
        if not entity:
            return None
        entity_type = getattr(entity, "type", None)
        if entity_type and entity_type in types:
            return entity
        current_id = getattr(entity, "parent_id", None)
    return None


def classify_entity_scope(registry: EntityRegistry, entity_id: SymbolID) -> str:
    module_types = {"PYTHON_MODULE", "JAVA_MODULE", "PACKAGE", "NAMESPACE_PACKAGE"}
    current_id = entity_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        entity = registry.get(current_id)
        if not entity:
            break
        entity_type = getattr(entity, "type", None)
        if entity_type == "CONTROL_FLOW_BLOCK":
            name = getattr(entity, "branch", "") or getattr(entity, "name", "")
            return f"conditional:{name}" if name else "conditional"
        if entity_type in module_types:
            return "module_level"
        current_id = getattr(entity, "parent_id", None)
    return "module_level"
