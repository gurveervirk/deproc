"""deproc_core: language-agnostic core runtime."""

from .config import Config
from .discovery import find_source_files
from .runtime import RuntimeRegistry, get_runtime_registry

__all__ = [
    "get_runtime_registry",
    "RuntimeRegistry",
    "find_source_files",
    "Config",
]
