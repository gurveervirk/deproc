from deproc.core.interfaces.parser.models import Node
from dataclasses import dataclass, field
from ..parser.models import (
    PythonModule,
    SymbolID,
)

@dataclass
class PythonNamespacePackage(Node):
    fqn: str
    submodule_ids: list[SymbolID] = field(default_factory=list)

@dataclass(kw_only=True)
class PythonPackage(PythonModule):
    submodule_ids: list[SymbolID] = field(default_factory=list)

__all__ = [
    "Node",
    "PythonNamespacePackage",
    "PythonPackage",
]
