"""
Use `Config` to:
- Access the runtime registry and registered plugins
- Get the list of selected languages and file extensions for processing
- Update the selected languages and file extensions using select_languages and select_file_extensions
"""
from .runtime import PluginRegistry

class _Config:
    def __init__(self):
        self._plugin_registry = PluginRegistry()
    
    @property
    def plugin_registry(self) -> PluginRegistry:
        return self._plugin_registry
    
    def get_languages(self) -> set[str]:
        return set(self.plugin_registry.supported_languages())
    
    def get_file_extensions(self) -> set[str]:
        return set(self.plugin_registry.supported_file_extensions())

Config = _Config()