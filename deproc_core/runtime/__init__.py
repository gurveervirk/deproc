from __future__ import annotations

from typing import Optional
from .registry import RuntimeRegistry

_RUNTIME_REGISTRY: Optional[RuntimeRegistry] = None

def get_runtime_registry() -> RuntimeRegistry:
    global _RUNTIME_REGISTRY
    if _RUNTIME_REGISTRY is None:
        registry = RuntimeRegistry()
        registry.discover()
        _RUNTIME_REGISTRY = registry
    return _RUNTIME_REGISTRY

__all__ = ["get_runtime_registry", "RuntimeRegistry"]
