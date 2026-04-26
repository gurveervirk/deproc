from __future__ import annotations

from pathlib import Path
from typing import Any

from tree_sitter import Parser

from .base import ParserPlugin, SourceParser
from .models import SourceFile


class ParserCore(SourceParser):
    """Centralized parser that delegates language details to plugins."""

    def __init__(self) -> None:
        self._plugins_by_extension: dict[str, ParserPlugin] = {}
        self._plugins_by_language: dict[str, ParserPlugin] = {}

    def register_plugin(self, plugin: ParserPlugin) -> None:
        self._plugins_by_language[plugin.language_id.lower()] = plugin
        for extension in plugin.file_extensions:
            self._plugins_by_extension[extension.lower()] = plugin

    def parse_file(self, file_path: str) -> SourceFile:
        path = Path(file_path)
        extension = path.suffix.lower()
        plugin = self._plugins_by_extension.get(extension)
        if plugin is None:
            raise ValueError(f"No parser plugin registered for extension: {extension}")

        source_bytes = path.read_bytes()
        source_code = source_bytes.decode("utf-8", errors="replace")

        parser = Parser(plugin.get_language())
        tree = parser.parse(source_bytes)

        captures: dict[str, list[Any]] = {}
        for entity_type, scm_query in plugin.get_queries().items():
            query = plugin.get_language().query(scm_query)
            raw_captures = query.captures(tree.root_node)
            captures[entity_type] = self._normalize_captures(raw_captures)

        return plugin.map_to_model(captures=captures, source_code=source_code, file_path=file_path)

    def get_plugin_for_extension(self, extension: str) -> ParserPlugin | None:
        return self._plugins_by_extension.get(extension.lower())

    def get_plugin_for_language(self, language: str) -> ParserPlugin | None:
        return self._plugins_by_language.get(language.lower())

    def list_registered_plugins(self) -> list[ParserPlugin]:
        return [self._plugins_by_language[key] for key in sorted(self._plugins_by_language.keys())]

    def list_registered_extensions(self) -> list[str]:
        return sorted(self._plugins_by_extension.keys())

    @staticmethod
    def _normalize_captures(raw_captures: object) -> list:
        """
        Normalize tree-sitter captures into a list[Node].

        Supports both common return shapes from tree-sitter Python bindings:
        - list[tuple[Node, str]]
        - dict[str, list[Node]]
        """
        if isinstance(raw_captures, dict):
            flattened: list = []
            for nodes in raw_captures.values():
                flattened.extend(nodes)
            return flattened

        if isinstance(raw_captures, list):
            if not raw_captures:
                return []
            first = raw_captures[0]
            if isinstance(first, tuple) and len(first) >= 1:
                return [item[0] for item in raw_captures if isinstance(item, tuple) and item]
            return raw_captures

        return []
