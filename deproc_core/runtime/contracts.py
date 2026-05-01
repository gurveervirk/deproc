from __future__ import annotations
from typing import Protocol

from ..interfaces import AliasFinder, ParserPlugin, SourceDiscovery

class LanguagePlugin(Protocol):
    language: str
    aliases: list[str]
    alias_finder: AliasFinder
    parser_plugin: ParserPlugin
    source_discovery: SourceDiscovery