from typing import Protocol, TypeVar, runtime_checkable
from ..parser.models import Node
from .models import AliasFinderResult

T_In = TypeVar("T_In", bound=list[Node])

@runtime_checkable
class AliasFinder(Protocol[T_In]):
    def find_aliases(self, nodes: T_In) -> AliasFinderResult:
        ...

__all__ = ["AliasFinder"]