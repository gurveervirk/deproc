from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TypeVar, cast

from ....interfaces.parser.models import (
    Entity,
    SemanticContainer,
    SymbolID,
)
from .utils import entity_fqn

T_SemanticContainer = TypeVar("T_SemanticContainer", bound=SemanticContainer)


@dataclass
class EntityRegistry:
    entities: dict[SymbolID, Entity] = field(default_factory=dict)
    fqn_to_ids: dict[str, set[SymbolID]] = field(
        default_factory=lambda: defaultdict(set)
    )

    def add(self, entity: Entity) -> None:
        assert entity.id is not None
        previous = self.entities.get(entity.id)
        if (
            previous is not None
            and previous is not entity
            and (
                isinstance(previous, SemanticContainer)
                or isinstance(entity, SemanticContainer)
            )
        ):
            raise ValueError(
                "Semantic containers must be merged with merge_semantic_container"
            )
        if previous is not None:
            previous_fqn = entity_fqn(previous)
            if previous_fqn:
                self.fqn_to_ids[previous_fqn].discard(entity.id)
                if not self.fqn_to_ids[previous_fqn]:
                    del self.fqn_to_ids[previous_fqn]
        self.entities[entity.id] = entity
        fqn = entity_fqn(entity)
        if fqn:
            self.fqn_to_ids[fqn].add(entity.id)

    def add_all(self, entities: list[Entity]) -> None:
        for entity in entities:
            self.add(entity)

    def merge_semantic_container(
        self, entity: T_SemanticContainer
    ) -> T_SemanticContainer:
        previous = self.entities.get(entity.id)
        if previous is None:
            self.add(entity)
            return entity
        if not isinstance(previous, SemanticContainer):
            raise ValueError("Semantic container ID collides with a non-container")
        previous.merge_from(entity)
        return cast(T_SemanticContainer, previous)

    def merge_from(self, other: EntityRegistry) -> None:
        for entity in other.values():
            if isinstance(entity, SemanticContainer):
                self.merge_semantic_container(entity)
            else:
                self.add(entity)

    def remove(self, entity_id: SymbolID) -> None:
        entity = self.entities.pop(entity_id, None)
        if entity is not None:
            fqn = entity_fqn(entity)
            if fqn and entity_id in self.fqn_to_ids.get(fqn, set()):
                self.fqn_to_ids[fqn].discard(entity_id)
                if not self.fqn_to_ids[fqn]:
                    del self.fqn_to_ids[fqn]

    def get_ids_by_fqn(self, fqn: str) -> set[SymbolID]:
        return set(self.fqn_to_ids.get(fqn, set()))

    def values(self):
        return self.entities.values()

    def get(self, entity_id: SymbolID, default=None):
        return self.entities.get(entity_id, default)

    def __contains__(self, entity_id: SymbolID) -> bool:
        return entity_id in self.entities
