from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable, Generic, TypeVar

T = TypeVar("T")

def _select_entry_points(group: str):
    discovered = entry_points()
    if hasattr(discovered, "select"):
        return discovered.select(group=group)
    return discovered.get(group, [])  # type: ignore[union-attr]

class PluginRegistry(Generic[T]):
    def __init__(
        self,
        *,
        group: str,
        validator: Callable[[object], bool] | None = None,
    ):
        self.group = group
        self.validator = validator
        self._plugins: dict[str, T] = {}

    def discover(self) -> dict[str, T]:
        for entry in _select_entry_points(self.group):
            loaded = entry.load()
            if self.validator is not None and not self.validator(loaded):
                continue
            self._plugins[entry.name] = loaded
        return dict(self._plugins)

    def register(self, name: str, plugin: T) -> None:
        self._plugins[name] = plugin

    def get_plugin(self, name: str) -> T | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins.keys())

