"""deproc_core: language-agnostic core runtime."""

from .api import get_registered_file_extensions, ignore_file_extensions, process_path
from .interfaces.parser import ParserPlugin
from .runtime import RuntimeRegistry, get_runtime_registry

__all__ = [
    "get_runtime_registry",
    "RuntimeRegistry",
    "get_registered_file_extensions",
    "ignore_file_extensions",
    "ParserPlugin",
    "process_path",
]
