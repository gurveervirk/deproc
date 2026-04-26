from __future__ import annotations

from typing import Dict, Protocol, runtime_checkable

from tree_sitter import Language, Node

from .models import SourceFile

@runtime_checkable
class SourceParser(Protocol):
    def parse_file(self, file_path: str) -> SourceFile:
        ...


@runtime_checkable
class ParserPlugin(Protocol):
    """Contract for language-specific tree-sitter parser plugins."""

    @property
    def language_id(self) -> str:
        """Return unique language identifier (for example: 'python')."""

    @property
    def file_extensions(self) -> list[str]:
        """Return handled file extensions (for example: ['.py'])."""

    def get_language(self) -> Language:
        """Return tree-sitter Language instance used by this plugin."""

    def get_queries(self) -> Dict[str, str]:
        """Return query map keyed by logical entity type."""

    def map_to_model(
        self,
        captures: Dict[str, list[Node]],
        source_code: str,
        file_path: str,
    ) -> SourceFile:
        """Map query captures into the core SourceFile model."""
