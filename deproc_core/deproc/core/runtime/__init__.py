from __future__ import annotations

from typing import Optional
from .registries import (
    EntityRegistry,
    PluginRegistry
)
from .contracts import LanguagePlugin

_RUNTIME_REGISTRY: Optional[PluginRegistry] = None

def get_runtime_registry() -> PluginRegistry:
    global _RUNTIME_REGISTRY
    if _RUNTIME_REGISTRY is None:
        registry = PluginRegistry()
        registry.discover()
        _RUNTIME_REGISTRY = registry
    return _RUNTIME_REGISTRY

__all__ = [
    "get_runtime_registry",
    "EntityRegistry",
    "PluginRegistry",
    "LanguagePlugin"
]
