from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...context import Context
    from .models import Node


@runtime_checkable
class SourceParser(Protocol):
    def parse_file(self, file_path: str, context: Context) -> Node: ...
