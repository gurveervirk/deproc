from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces.linker import Linker
    from .interfaces.parser import SourceParser
    from .interfaces.resolver import Resolver
    from .interfaces.symbol_cache import SymbolCache

from .runtime import EntityRegistry

logger = logging.getLogger(__name__)

class Context:
    def __init__(self, base_path: str = "", copy_from: Context | None = None):
        if copy_from:
            self.base_path = copy_from.base_path
            self.entity_registry = copy_from.entity_registry
            self._language_aliases = dict(copy_from._language_aliases)
            self._language_extensions = dict(copy_from._language_extensions)
            self._all_languages = set(copy_from._all_languages)
            self._all_file_extensions = set(copy_from._all_file_extensions)
            self._selected_languages = set(copy_from._selected_languages)
            self._selected_file_extensions = set(copy_from._selected_file_extensions)
            self._parsers = dict(copy_from._parsers)
            self._resolvers = dict(copy_from._resolvers)
            self._linkers = dict(copy_from._linkers)
            self.symbol_caches = dict(copy_from.symbol_caches)
        else:
            self.base_path = base_path
            self.entity_registry = EntityRegistry()
            self._language_aliases: dict[str, list[str]] = {}
            self._language_extensions: dict[str, list[str]] = {}
            self._all_languages: set[str] = set()
            self._all_file_extensions: set[str] = set()
            self._selected_languages: set[str] = set()
            self._selected_file_extensions: set[str] = set()
            self._parsers: dict[str, SourceParser] = {}
            self._resolvers: dict[str, Resolver] = {}
            self._linkers: dict[str, Linker] = {}
            self.symbol_caches: dict[str, SymbolCache] = {}

    def set_language(
        self,
        language: str,
        file_extensions: list[str],
        aliases: list[str] | None = None,
    ) -> None:
        normalized = language.strip().lower()
        normalized_extensions: list[str] = []
        for ext in file_extensions:
            e = ext.strip().lower()
            if not e.startswith("."):
                e = f".{e}"
                logger.warning("Normalized file extension '%s' to '%s' for language '%s'", ext, e, normalized)
            normalized_extensions.append(e)
        self._language_extensions[normalized] = normalized_extensions
        if aliases:
            self._language_aliases[normalized] = [a.strip().lower() for a in aliases]
        else:
            self._language_aliases[normalized] = []
        self._all_languages.add(normalized)
        self._selected_languages.add(normalized)
        self._all_file_extensions.update(normalized_extensions)
        self._selected_file_extensions.update(normalized_extensions)

    @property
    def selected_languages(self) -> set[str]:
        return self._selected_languages

    @property
    def selected_file_extensions(self) -> set[str]:
        return self._selected_file_extensions

    def _normalize_language(self, language: str) -> str:
        normalized = language.strip().lower()
        for canonical, aliases in self._language_aliases.items():
            if normalized == canonical or normalized in aliases:
                return canonical
        return normalized

    def _normalize_extension(self, extension: str) -> str:
        normalized = extension.strip().lower()
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        return normalized

    def select_languages(self, languages: list[str]) -> None:
        for lang in languages:
            normalized = self._normalize_language(lang)
            exclude = normalized.startswith("!")
            if exclude:
                normalized = normalized[1:]
            if normalized in self._all_languages:
                if exclude:
                    self._selected_languages.discard(normalized)
                else:
                    self._selected_languages.add(normalized)

    def select_file_extensions(self, extensions: list[str]) -> None:
        for ext in extensions:
            raw = ext.strip().lower()
            exclude = raw.startswith("!")
            if exclude:
                raw = raw[1:]
            normalized = self._normalize_extension(raw)
            if normalized in self._all_file_extensions:
                if exclude:
                    self._selected_file_extensions.discard(normalized)
                else:
                    self._selected_file_extensions.add(normalized)

    def _require_language(self, language: str) -> None:
        if language not in self._all_languages:
            raise KeyError(f"Language '{language}' is not registered. Call set_language() first.")

    def _warn_if_language_missing(self, language: str) -> None:
        if language not in self._all_languages:
            logger.warning("Language '%s' is not registered. Did you forget to call set_language()?", language)

    def set_parser(self, language: str, parser: SourceParser) -> None:
        self._require_language(language)
        self._parsers[language] = parser

    def get_parser(self, language: str) -> SourceParser | None:
        self._warn_if_language_missing(language)
        return self._parsers.get(language)

    def has_parser(self, language: str) -> bool:
        self._warn_if_language_missing(language)
        return language in self._parsers

    def remove_parser(self, language: str) -> None:
        self._warn_if_language_missing(language)
        self._parsers.pop(language, None)

    def set_resolver(self, language: str, resolver: Resolver) -> None:
        self._require_language(language)
        self._resolvers[language] = resolver

    def get_resolver(self, language: str) -> Resolver | None:
        self._warn_if_language_missing(language)
        return self._resolvers.get(language)

    def has_resolver(self, language: str) -> bool:
        self._warn_if_language_missing(language)
        return language in self._resolvers

    def remove_resolver(self, language: str) -> None:
        self._warn_if_language_missing(language)
        self._resolvers.pop(language, None)

    def set_linker(self, language: str, linker: Linker) -> None:
        self._require_language(language)
        self._linkers[language] = linker

    def get_linker(self, language: str) -> Linker | None:
        self._warn_if_language_missing(language)
        return self._linkers.get(language)

    def has_linker(self, language: str) -> bool:
        self._warn_if_language_missing(language)
        return language in self._linkers

    def remove_linker(self, language: str) -> None:
        self._warn_if_language_missing(language)
        self._linkers.pop(language, None)

    def set_symbol_cache(self, cache: SymbolCache) -> None:
        self._require_language(cache.language)
        self.symbol_caches[cache.language] = cache

    def get_symbol_cache(self, language: str) -> SymbolCache | None:
        self._warn_if_language_missing(language)
        return self.symbol_caches.get(language)

    def has_symbol_cache(self, language: str) -> bool:
        self._warn_if_language_missing(language)
        return language in self.symbol_caches

    def remove_symbol_cache(self, language: str) -> None:
        self._warn_if_language_missing(language)
        self.symbol_caches.pop(language, None)

    def reset(
        self,
        include_languages: bool = True,
        include_file_extensions: bool = True,
        include_symbol_caches: bool = True,
    ) -> None:
        if include_languages:
            self._selected_languages = set(self._all_languages)
        if include_file_extensions:
            self._selected_file_extensions = set(self._all_file_extensions)
        if include_symbol_caches:
            self.symbol_caches = {}
