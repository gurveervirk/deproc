from deproc.core.interfaces.parser.models import Node
from dataclasses import dataclass, field
from ..parser.models import SymbolID

@dataclass(kw_only=True)
class JavaPackage(Node):
    fqn: str
    subpackage_ids: list[SymbolID] = field(default_factory=list)
    compilation_unit_ids: list[SymbolID] = field(default_factory=list)

__all__ = [
    "Node",
    "JavaPackage",
]
