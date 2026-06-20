"""
Use `Config` to:
- Access the runtime registry and registered plugins
- Get the list of selected languages and file extensions for processing
- Update the selected languages and file extensions using select_languages and select_file_extensions
"""
from .runtime import get_runtime_registry, PluginRegistry

class _Config:
    def __init__(self):
        self._runtime_registry = get_runtime_registry()
        self._file_extensions = set(self._runtime_registry._file_extensions.keys())
        self._languages = set(self._runtime_registry._plugin_classes.keys())
    
    @property
    def runtime_registry(self) -> PluginRegistry:
        return self._runtime_registry
    
    def get_languages(self) -> set[str]:
        return self._languages
    
    def get_file_extensions(self) -> set[str]:
        return self._file_extensions

Config = _Config()