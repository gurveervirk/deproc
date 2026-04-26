from __future__ import annotations

from typing import Type

from ..registry import PluginRegistry
from .contracts import LanguagePlugin

class RuntimeRegistry:
    def __init__(self, entry_point_group: str = "deproc.languages"):
        self._entry_point_group = entry_point_group
        self._plugin_classes: dict[str, Type[LanguagePlugin]] = {}
        self._aliases: dict[str, str] = {}

    def register(self, plugin_cls: Type[LanguagePlugin]) -> None:
        plugin = plugin_cls()
        canonical = plugin.language.strip().lower()
        self._plugin_classes[canonical] = plugin_cls
        for alias in plugin.aliases:
            self._aliases[alias.strip().lower()] = canonical

    def discover(self) -> None:
        registry = PluginRegistry[Type[LanguagePlugin]](
            group=self._entry_point_group,
            validator=lambda loaded: isinstance(loaded, type)
            and issubclass(loaded, LanguagePlugin),
        )
        discovered = registry.discover()
        for plugin_cls in discovered.values():
            self.register(plugin_cls)

    def supported_languages(self) -> list[str]:
        return sorted(self._plugin_classes.keys())

    def normalize_language(self, language: str) -> str:
        normalized = (language or "").strip().lower()
        if not normalized:
            return ""
        return self._aliases.get(normalized, normalized)

    def get_plugin(self, language: str) -> LanguagePlugin:
        language = self.normalize_language(language)
        plugin_cls = self._plugin_classes.get(language)
        if plugin_cls is None:
            available = ", ".join(self.supported_languages())
            raise ImportError(
                f"Language plugin '{language}' is not installed. "
                f"Available languages: {available or '(none)'}."
            )
        return plugin_cls()
