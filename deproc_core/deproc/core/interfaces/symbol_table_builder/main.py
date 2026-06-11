from typing import Protocol, runtime_checkable
from .models import SymbolTable
from ...context import Context

@runtime_checkable
class SymbolTableBuilder(Protocol):
    def build(self, context: Context) -> SymbolTable:
        ...

__all__ = ["SymbolTableBuilder"]