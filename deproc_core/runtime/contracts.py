from __future__ import annotations
from typing import Protocol

from ..interfaces import SourceParser, SourceDiscovery, AliasFinder

class LanguagePlugin(Protocol):
    language: str
    aliases: list[str]
    alias_finder: AliasFinder
    source_parser: SourceParser
    source_discovery: SourceDiscovery