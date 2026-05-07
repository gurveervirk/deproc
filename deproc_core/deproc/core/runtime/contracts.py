from dataclasses import dataclass
from ..interfaces import AliasFinder, SourceParser

@dataclass
class LanguagePlugin:
    language: str
    aliases: list[str]
    file_extensions: list[str]
    alias_finder: AliasFinder
    source_parser: SourceParser