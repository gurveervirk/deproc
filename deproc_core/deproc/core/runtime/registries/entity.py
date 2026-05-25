from dataclasses import dataclass, field
from ...interfaces.parser.models import Entity

@dataclass
class EntityRegistry:
    """
    A flat registry tracking all parsed entities by their ID.
    Used by downstream processors to resolve string IDs into full object references.
    """
    entities: dict[str, Entity] = field(default_factory=dict)
    
    def add(self, entity: Entity) -> None:
        """Register a parsed entity."""
        self.entities[entity.id] = entity

    def add_all(self, entities: list[Entity]) -> None:
        """Register multiple parsed entities at once."""
        for entity in entities:
            self.add(entity)
        
    def get(self, entity_id: str) -> Entity | None:
        """Resolve a string ID back to the Entity object."""
        return self.entities.get(entity_id)

    def __contains__(self, entity_id: str) -> bool:
        return entity_id in self.entities
