from dataclasses import dataclass
from ..extraction.models import Entity

@dataclass
class ModelConversionResult:
    entities: list[Entity]