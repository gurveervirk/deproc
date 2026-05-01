from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .interfaces.parser import SourceFile
from .interfaces.parser.registry import (
    get_parser_core,
    get_registered_file_extensions as _get_registered_file_extensions,
    ignore_file_extensions as _ignore_file_extensions,
)
from .runtime import get_runtime_registry


@dataclass
class ProcessPathResult:
    """Generic result for processing a filesystem path via language plugin ecosystem."""

    language: str
    root_path: str
    parsed_files: list[SourceFile] = field(default_factory=list)
    failed_files: dict[str, str] = field(default_factory=dict)


def get_registered_file_extensions() -> list[str]:
    """Return currently active parser extensions after ignore rules are applied."""
    return _get_registered_file_extensions()


def ignore_file_extensions(extensions: list[str]) -> None:
    """Ignore one or more file extensions across discovery and process_path."""
    _ignore_file_extensions(extensions)


def process_path(path: str, language: str) -> ProcessPathResult:
    """
    Process a file or directory using the centralized parser core and language plugin discovery.
    """
    runtime = get_runtime_registry()
    plugin = runtime.get_plugin(language)
    parser_core = get_parser_core()

    # Ensure the parser plugin is registered even when registry was manually populated.
    parser_core.register_plugin(plugin.parser_plugin)

    root = Path(path)
    discovered_files = plugin.source_discovery.find_source_files(str(root))
    result = ProcessPathResult(
        language=runtime.normalize_language(language),
        root_path=str(root),
    )

    for file_path in discovered_files:
        try:
            parsed = parser_core.parse_file(file_path)
            result.parsed_files.append(parsed)
        except Exception as exc:
            result.failed_files[file_path] = str(exc)

    return result
