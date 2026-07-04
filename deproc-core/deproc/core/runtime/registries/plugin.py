from __future__ import annotations
from typing import Type
from ..contracts import LanguagePlugin

class PluginRegistry:
    """
    Discovers, registers, and provides access to Language Plugins
    """
    def __init__(self):
        self._plugins: dict[str, LanguagePlugin] = {}
        self._aliases: dict[str, str] = {}
        self._file_extensions: dict[str, str] = {}

    def register(self, plugin: LanguagePlugin) -> None:
        canonical_language = plugin.language.strip().lower()
        self._plugins[canonical_language] = plugin

        for alias in plugin.aliases:
            self._aliases[alias.strip().lower()] = canonical_language
        
        for ext in plugin.file_extensions:
            self._file_extensions[ext.strip().lower()] = canonical_language

    def supported_languages(self) -> list[str]:
        return sorted(self._plugins.keys())
    
    def supported_file_extensions(self) -> list[str]:
        return sorted(self._file_extensions.keys())

    def normalize_language(self, language: str) -> str:
        normalized = (language or "").strip().lower()
        if not normalized:
            return ""
        return self._aliases.get(normalized, normalized)

    def normalize_extension(self, extension: str) -> str:
        normalized = (extension or "").strip().lower()
        if not normalized:
            return ""
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        return self._file_extensions.get(normalized, normalized)

    def get_plugin_by_language(self, language: str) -> LanguagePlugin:
        language = self.normalize_language(language)
        plugin = self._plugins.get(language)
        if plugin is None:
            available = ", ".join(self.supported_languages())
            raise ImportError(
                f"Language plugin '{language}' is not installed. "
                f"Available languages: {available or '(none)'}."
            )
        return plugin

    def get_plugin_by_extension(self, extension: str) -> LanguagePlugin:
        extension = self.normalize_extension(extension)
        language = self._file_extensions.get(extension)
        if language is None:
            available = ", ".join(self.supported_file_extensions())
            raise ImportError(
                f"No language plugin registered for file extension '{extension}'. "
                f"Available extensions: {available or '(none)'}."
            )
        return self.get_plugin_by_language(language)
    
    def get_file_extensions_for_language(self, language: str) -> list[str]:
        language = self.normalize_language(language)
        return sorted(ext for ext, lang in self._file_extensions.items() if lang == language)
