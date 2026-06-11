from typing import Protocol, TypeVar, runtime_checkable
from ..context import Context

T_Out = TypeVar("T_Out")

@runtime_checkable
class SymbolTableBuilder(Protocol[T_Out]):
    def build(self, context: Context) -> T_Out:
        ...

__all__ = ["SymbolTableBuilder"]