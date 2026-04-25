from __future__ import annotations

from typing import Any, Iterable, Protocol, runtime_checkable

from .models import Entity, Relationship


@runtime_checkable
class SourceParser(Protocol):
    def parse_file(self, file_path: str) -> Any: ...


@runtime_checkable
class ParserProvider(Protocol):
    def create_parser(self) -> SourceParser: ...


@runtime_checkable
class SourceDiscovery(Protocol):
    file_extensions: tuple[str, ...]

    def find_source_files(self, root_path: str) -> Iterable[str]: ...


@runtime_checkable
class AliasFinder(Protocol):
    def find_aliases(
        self,
        entities: list[Entity],
        relations: list[Relationship],
        other_relations: dict[str, Any],
        module_symbol_maps: dict[str, list[dict[str, Any]]] | None = None,
    ) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[dict[str, Any]]]]: ...
