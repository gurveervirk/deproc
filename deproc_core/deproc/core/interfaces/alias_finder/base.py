from typing import Protocol, TypeVar, runtime_checkable
from ..parser.models import Node
from .models import AliasFinderResult

T_Context = TypeVar("T_Context", bound=list[Node] | Node)

@runtime_checkable
class AliasFinder(Protocol[T_Context]):
    def find_aliases(self, extraction_context: T_Context) -> AliasFinderResult:
        ...

__all__ = ["AliasFinder"]