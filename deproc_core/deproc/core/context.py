from .config import Config
from .runtime import EntityRegistry

class Context:
    def __init__(self, base_path: str = "", copy_from: "Context | None" = None):
        if copy_from:
            self.base_path = copy_from.base_path
            self.entity_registry = copy_from.entity_registry
            self._file_extensions = set(copy_from._file_extensions)
            self._languages = set(copy_from._languages)
            self._selected_languages = set(copy_from._selected_languages)
            self._selected_file_extensions = set(copy_from._selected_file_extensions)
        else:
            self.base_path = base_path
            self.entity_registry = EntityRegistry()
            self._file_extensions = set(Config.get_file_extensions())
            self._languages = set(Config.get_languages())
            self._selected_languages = set(self._languages)
            self._selected_file_extensions = set(self._file_extensions)

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
