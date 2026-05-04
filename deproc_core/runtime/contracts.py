from __future__ import annotations
from typing import Protocol

from ..interfaces import AliasFinder, SourceParser

class LanguagePlugin(Protocol):
    language: str
    aliases: list[str]
    file_extensions: list[str]
    alias_finder: AliasFinder
    source_parser: SourceParser