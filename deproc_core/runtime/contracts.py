from __future__ import annotations
from typing import Protocol

from ..interfaces import AliasFinder, ParserPlugin, SourceDiscovery, SourceParser

class LanguagePlugin(Protocol):
    language: str
    aliases: list[str]
    alias_finder: AliasFinder
    source_parser: SourceParser
    parser_plugin: ParserPlugin
    source_discovery: SourceDiscovery