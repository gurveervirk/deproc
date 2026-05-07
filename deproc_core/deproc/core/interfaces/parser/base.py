from __future__ import annotations

from typing import Protocol, runtime_checkable
from .models import SourceFile

@runtime_checkable
class SourceParser(Protocol):
    def parse_file(self, file_path: str) -> SourceFile:
        ...