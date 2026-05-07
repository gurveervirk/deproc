from typing import Protocol, Tuple, TypeVar, runtime_checkable
from ..model_conversion import ExtractionContext
from .models import AliasFinderResult

T_Context = TypeVar("T_Context", bound=ExtractionContext)

@runtime_checkable
class AliasFinder(Protocol[T_Context]):
    def find_aliases(self, extraction_context: T_Context) -> AliasFinderResult:
        ...

__all__ = ["AliasFinder"]