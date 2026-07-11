from collections import defaultdict
from dataclasses import dataclass, field
from ...interfaces.parser.models import (
    Entity,
    SymbolID,
)

@dataclass
class EntityRegistry:
    entities: dict[SymbolID, Entity] = field(default_factory=dict)
    fqn_to_ids: dict[str, set[SymbolID]] = field(default_factory=lambda: defaultdict(set))

    def add(self, entity: Entity) -> None:
        self.entities[entity.id] = entity
        fqn = getattr(entity, "fqn", None)
        if fqn:
            self.fqn_to_ids[fqn].add(entity.id)

    def add_all(self, entities: list[Entity]) -> None:
        for entity in entities:
            self.add(entity)

    def remove(self, entity_id: SymbolID) -> None:
        entity = self.entities.pop(entity_id, None)
        if entity is not None:
            fqn = getattr(entity, "fqn", None)
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
