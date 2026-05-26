from deproc.core.interfaces.parser.models import (
    SourceFile,
    Node,
)
from dataclasses import dataclass, field

@dataclass(kw_only=True)
class PythonModule(SourceFile):
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
