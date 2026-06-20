from __future__ import annotations
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .models import SymbolTable
    from ...context import Context

@runtime_checkable
class SymbolTableBuilder(Protocol):
    def build(self, context: Context) -> SymbolTable:
        ...

__all__ = ["SymbolTableBuilder"]