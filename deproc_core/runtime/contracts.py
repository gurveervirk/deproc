from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from ..models import Entity, Relationship

from ..interfaces import SourceParser


class ParserProvider(ABC):
    @abstractmethod
    def create_parser(self) -> SourceParser:
        raise NotImplementedError


class SourceDiscovery(ABC):
    file_extensions: tuple[str, ...] = tuple()

    @abstractmethod
    def find_source_files(self, root_path: str) -> Iterable[str]:
        raise NotImplementedError


class AliasFinder(ABC):
    @abstractmethod
    def find_aliases(
        self,
        entities: list[Entity],
        relations: list[Relationship],
        other_relations: dict[str, Any],
        module_symbol_maps: dict[str, list[dict[str, Any]]] | None = None,
    ) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[dict[str, Any]]]]:
        raise NotImplementedError


class LanguagePlugin(ABC):
    language: str
    aliases: tuple[str, ...] = tuple()

    parser_provider: ParserProvider
    source_discovery: SourceDiscovery | None
    alias_finder: AliasFinder | None
