from dataclasses import dataclass, field

from deproc.core.interfaces.parser.models import Node, SemanticContainer

from ..parser.models import (
    PythonModule,
    SymbolID,
)


@dataclass
class PythonNamespacePackage(SemanticContainer):
    path: str
    fqn: str
    submodule_ids: list[SymbolID] = field(default_factory=list)

    @property
    def semantic_type(self) -> str:
        return "python.namespace-package"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.submodule_ids = sorted(set(self.submodule_ids))

    @property
    def contribution_ids(self) -> list[SymbolID]:
        return self.submodule_ids

    def _merge_contributions(self, other: SemanticContainer) -> None:
        if not isinstance(other, PythonNamespacePackage):
            raise ValueError(
                "Namespace packages can only merge with namespace packages"
            )
        self.submodule_ids = sorted(set(self.submodule_ids) | set(other.submodule_ids))


@dataclass(kw_only=True)
class PythonPackage(PythonModule):
    submodule_ids: list[SymbolID] = field(default_factory=list)


__all__ = [
    "Node",
    "PythonNamespacePackage",
    "PythonPackage",
]
