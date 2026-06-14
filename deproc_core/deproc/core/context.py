from .config import Config
from .runtime import EntityRegistry
from .interfaces.symbol_table_builder.models import SymbolTable
from .interfaces.symbol_cache import SymbolCache

class Context:
    def __init__(self, base_path: str = "", copy_from: "Context | None" = None):
        if copy_from:
            self.base_path = copy_from.base_path
            self.entity_registry = copy_from.entity_registry
            self._file_extensions = set(copy_from._file_extensions)
            self._languages = set(copy_from._languages)
            self._selected_languages = set(copy_from._selected_languages)
            self._selected_file_extensions = set(copy_from._selected_file_extensions)
            self.symbol_tables = copy_from.symbol_tables
            self.symbol_caches = copy_from.symbol_caches
        else:
            self.base_path = base_path
            self.entity_registry = EntityRegistry()
            self._file_extensions = set(Config.get_file_extensions())
            self._languages = set(Config.get_languages())
            self._selected_languages = set(self._languages)
            self._selected_file_extensions = set(self._file_extensions)
            self.symbol_tables = {}
            self.symbol_caches = {}

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
            normalized = Config.runtime_registry.normalize_language(lang)
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
            normalized = Config.runtime_registry.normalize_extension(ext)
            if normalized in self._file_extensions:
                if ext.startswith("!"):
                    self._selected_file_extensions.discard(normalized)
                else:
                    self._selected_file_extensions.add(normalized)

    def add_symbol_table(self, symbol_table: SymbolTable) -> None:
        self.symbol_tables[symbol_table.language] = symbol_table

    def get_symbol_table(self, language: str) -> SymbolTable | None:
        return self.symbol_tables.get(language, None)
    
    def has_symbol_table(self, language: str) -> bool:
        return language in self.symbol_tables
    
    def remove_symbol_table(self, language: str) -> None:
        if language in self.symbol_tables:
            del self.symbol_tables[language]

    def add_symbol_cache(self, cache: SymbolCache) -> None:
        self.symbol_caches[cache.language] = cache

    def get_symbol_cache(self, language: str) -> SymbolCache | None:
        return self.symbol_caches.get(language, None)
    
    def has_symbol_cache(self, language: str) -> bool:
        return language in self.symbol_caches
    
    def remove_symbol_cache(self, language: str) -> None:
        if language in self.symbol_caches:
            del self.symbol_caches[language]

    def reset(
        self,
        include_languages: bool = True,
        include_file_extensions: bool = True,
        include_symbol_tables: bool = True,
        include_symbol_caches: bool = True
    ) -> None:
        """
        Reset selected languages, file extensions and clear symbol tables and caches.
        """
        if include_languages:
            self._selected_languages = set(self._languages)
        if include_file_extensions:
            self._selected_file_extensions = set(self._file_extensions)
        if include_symbol_tables:
            self.symbol_tables = {}
        if include_symbol_caches:
            self.symbol_caches = {}