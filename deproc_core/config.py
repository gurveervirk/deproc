"""
Use SETTINGS to:
- Access the runtime registry and registered plugins
- Get the list of selected languages and file extensions for processing
- Update the selected languages and file extensions using select_languages and select_file_extensions
"""
from __future__ import annotations

from .runtime import get_runtime_registry, RuntimeRegistry

class _Config:
    def __init__(self):
        self._runtime_registry = get_runtime_registry()
        self._file_extensions = set(self._runtime_registry._file_extensions.keys())
        self._languages = set(self._runtime_registry._plugin_classes.keys())
        self._selected_languages = set(self._languages)
        self._selected_file_extensions = set(self._file_extensions)
    
    @property
    def runtime_registry(self) -> RuntimeRegistry:
        return self._runtime_registry

    @property
    def selected_languages(self) -> set[str]:
        return self._selected_languages

    @property
    def selected_file_extensions(self) -> set[str]:
        return self._selected_file_extensions

    def select_languages(self, languages: list[str]) -> None:
        """
        Select languages to include in processing. Use ! before a language to exclude it. Example: ["python", "!javascript"]
        """
        for lang in languages:
            normalized = self._runtime_registry.normalize_language(lang)
            if normalized in self._languages:
                if lang.startswith("!"):
                    self._selected_languages.discard(normalized)
                else:
                    self._selected_languages.add(normalized)

    def select_file_extensions(self, extensions: list[str]) -> None:
        """
        Select file extensions to include in processing. Use ! before an extension to exclude it. Example: [".py", "!.js"]
        """
        for ext in extensions:
            normalized = self._runtime_registry.normalize_extension(ext)
            if normalized in self._file_extensions:
                if ext.startswith("!"):
                    self._selected_file_extensions.discard(normalized)
                else:
                    self._selected_file_extensions.add(normalized)

    def reset(
        self,
        include_languages: bool = True,
        include_file_extensions: bool = True,
    ) -> None:
        """
        Reset selected languages and file extensions to include all available.
        """
        if include_languages:
            self._selected_languages = set(self._languages)
        if include_file_extensions:
            self._selected_file_extensions = set(self._file_extensions)

Config = _Config()