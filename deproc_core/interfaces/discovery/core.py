from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..parser import ParserCore, get_parser_core


class CoreSourceDiscovery:
    """Discovery implementation driven by parser plugin registrations."""

    def __init__(self, parser_core: ParserCore | None = None) -> None:
        self._parser_core = parser_core or get_parser_core()

    @property
    def file_extensions(self) -> tuple[str, ...]:
        return tuple(self._parser_core.list_effective_extensions())

    def find_source_files(self, root_path: str) -> Iterable[str]:
        root = Path(root_path)
        extension_set = set(self.file_extensions)
        if not extension_set:
            return []

        matches: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in extension_set:
                matches.append(str(path))

        matches.sort()
        return matches
