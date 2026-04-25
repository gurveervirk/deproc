from __future__ import annotations

import os
from typing import Any, Iterable

from tree_sitter import Language, Parser
import tree_sitter_python

from deproc_core.base import BaseAliasFinder, BaseParserProvider, BaseSourceDiscovery
from deproc_core.models import Entity, Relationship
from deproc_core.runtime.contracts import LanguagePlugin


class PythonPluginParser:
    def __init__(self) -> None:
        language = Language(tree_sitter_python.language())
        self._parser = Parser(language)

    def parse_file(self, file_path: str) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            source_bytes = f.read()
        tree = self._parser.parse(source_bytes)
        return {
            "file_path": file_path,
            "language": "python",
            "root_type": tree.root_node.type,
            "source": source_bytes.decode("utf-8", errors="replace"),
        }


class PythonParserProvider(BaseParserProvider):
    def create_parser(self) -> PythonPluginParser:
        return PythonPluginParser()


class PythonSourceDiscovery(BaseSourceDiscovery):
    file_extensions = (".py", ".pyi")

    def find_source_files(self, root_path: str) -> Iterable[str]:
        self._validate_root(root_path)
        if os.path.isfile(root_path):
            if root_path.endswith(self.file_extensions):
                yield root_path
            return
        for root, _, files in os.walk(root_path):
            py_stems: set[str] = set()
            pyi_stems: dict[str, str] = {}
            for file in files:
                if file.endswith(".py"):
                    py_stems.add(file[:-3])
                    yield os.path.join(root, file)
                elif file.endswith(".pyi"):
                    pyi_stems[file[:-4]] = os.path.join(root, file)
            for stem, path in pyi_stems.items():
                if stem not in py_stems:
                    yield path


class PythonAliasFinder(BaseAliasFinder):
    def find_aliases(
        self,
        entities: list[Entity],
        relations: list[Relationship],
        other_relations: dict[str, Any],
        module_symbol_maps: dict[str, list[dict[str, Any]]] | None = None,
    ) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[dict[str, Any]]]]:
        self._validate_relations(other_relations)
        return {}, {}


class PythonLanguagePlugin(LanguagePlugin):
    language = "python"
    aliases = ("py",)

    def __init__(self) -> None:
        self.parser_provider = PythonParserProvider()
        self.source_discovery = PythonSourceDiscovery()
        self.alias_finder = PythonAliasFinder()


__all__ = ["PythonLanguagePlugin"]

