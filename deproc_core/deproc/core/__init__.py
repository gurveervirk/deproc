"""deproc_core: language-agnostic core runtime."""

from .config import Config
from .discovery import find_source_files
from .runtime import (
    get_runtime_registry,
    RuntimeRegistry,
    LanguagePlugin
)
from .processor import ProcessPathResult, process_path

__all__ = [
    "get_runtime_registry",
    "RuntimeRegistry",
    "LanguagePlugin",
    "find_source_files",
    "Config",
    "process_path",
    "ProcessPathResult"
]
