from __future__ import annotations

from .discovery import find_source_files
from .config import Config
from .interfaces.parser.models import SourceFile

from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ProcessPathResult:
    selected_languages: set[str]
    selected_extensions: set[str]
    root_path: str
    parsed_files: list[SourceFile] = field(default_factory=list)
    failed_files: dict[str, str] = field(default_factory=dict)

def process_path(path: str) -> ProcessPathResult:
    """
    Process a file or directory using the centralized parser core and language plugin discovery.
    """
    runtime = Config.runtime_registry
    selected_languages = Config.selected_languages
    selected_extensions = Config.selected_file_extensions
    parsers = {extension: runtime.get_plugin_by_extension(extension).source_parser for extension in selected_extensions}

    root = Path(path)
    discovered_files = find_source_files(str(root), selected_extensions)

    result = ProcessPathResult(
        selected_languages=selected_languages,
        selected_extensions=selected_extensions,
        root_path=str(root),
    )
    for file_path in discovered_files:
        try:
            extension = Path(file_path).suffix
            parser = parsers.get(extension)

            if parser is None:
                raise ValueError(f"No parser registered for extension: {extension}")
            
            parsed = parser.parse_file(file_path)
            result.parsed_files.append(parsed)
        except Exception as exc:
            result.failed_files[file_path] = str(exc)

    return result
