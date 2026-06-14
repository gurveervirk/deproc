from dataclasses import dataclass
from ..interfaces import SymbolTableBuilder, SourceParser

@dataclass
class LanguagePlugin:
    language: str
    aliases: list[str]
    file_extensions: list[str]
    symbol_table_builder: SymbolTableBuilder
    source_parser: SourceParser