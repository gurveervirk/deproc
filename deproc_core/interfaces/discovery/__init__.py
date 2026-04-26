from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from .core import CoreSourceDiscovery

@runtime_checkable
class SourceDiscovery(Protocol):
    file_extensions: tuple[str, ...]

    def find_source_files(self, root_path: str) -> Iterable[str]: ...

__all__ = ["SourceDiscovery", "CoreSourceDiscovery"]