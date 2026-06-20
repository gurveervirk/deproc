from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..interfaces import (
        Linker,
        Resolver,
        SourceParser,
        SymbolCache,
        SymbolTableBuilder,
    )

@dataclass
class LanguagePlugin:
    language: str
    aliases: list[str]
    file_extensions: list[str]
    linker: Linker
    resolver: Resolver
    source_parser: SourceParser
    symbol_cache: SymbolCache
    symbol_table_builder: SymbolTableBuilder