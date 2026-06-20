from __future__ import annotations
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .models import SourceFile
    from ...context import Context

@runtime_checkable
class SourceParser(Protocol):
    def parse_file(self, file_path: str, context: Context) -> SourceFile:
        ...