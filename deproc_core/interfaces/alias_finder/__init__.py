from __future__ import annotations

from typing import Optional, Protocol, Tuple, runtime_checkable
from ...models import Entity, Relationship, ExternalEntityRef

@runtime_checkable
class AliasFinder(Protocol):
    def find_aliases(
        self,
        entities: list[Entity],
        relations: list[Relationship],
        other_relations: dict[str, list[Tuple[str, ExternalEntityRef]]],
        module_symbol_maps: Optional[dict[str, list[dict]]] = None,
    ) -> Tuple[dict[str, list[str]], dict[Tuple[str, str], list[dict]]]: ...
    
__all__ = ["AliasFinder"]