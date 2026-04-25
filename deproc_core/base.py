from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from .models import Entity, Relationship

from .interfaces import SourceParser


class BaseParserProvider(ABC):
    @abstractmethod
    def create_parser(self) -> SourceParser:
        raise NotImplementedError


class BaseSourceDiscovery(ABC):
    file_extensions: tuple[str, ...] = tuple()

    def _validate_root(self, root_path: str) -> None:
        if not root_path:
            raise ValueError("root_path cannot be empty.")

    @abstractmethod
    def find_source_files(self, root_path: str) -> Iterable[str]:
        raise NotImplementedError


class BaseAliasFinder(ABC):
    def _validate_relations(self, other_relations: dict[str, Any]) -> None:
        if other_relations is None:
            raise ValueError("other_relations cannot be None.")

    @abstractmethod
    def find_aliases(
        self,
        entities: list[Entity],
        relations: list[Relationship],
        other_relations: dict[str, Any],
        module_symbol_maps: dict[str, list[dict[str, Any]]] | None = None,
    ) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[dict[str, Any]]]]:
        raise NotImplementedError
