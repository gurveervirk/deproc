from dataclasses import dataclass
from ..extraction.models import Entity

@dataclass
class ExtractionContext:
    entities: list[Entity]