from deproc.core.interfaces.parser.models import Node
from dataclasses import dataclass, field
from ..parser.models import PythonSourceFile

@dataclass(kw_only=True)
class PythonModule(PythonSourceFile):
    fqn: str

@dataclass
class PythonNamespacePackage(Node):
    fqn: str
    submodule_ids: list[str] = field(default_factory=list)

@dataclass(kw_only=True)
class PythonPackage(PythonModule):
    submodule_ids: list[str] = field(default_factory=list)

__all__ = [
    "Node",
    "PythonModule",
    "PythonNamespacePackage",
    "PythonPackage",
    "SourceFile",
]
