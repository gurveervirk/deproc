from __future__ import annotations
from deproc.core.interfaces.symbol_cache import SymbolCache
from .models import (
    cache_key,
    cache_value,
    compilation_unit_fqn,
    symbol_name,
)

class JavaSymbolCache(SymbolCache[dict, cache_value | None]):
    def __init__(self):
        self.language = "java"
        self.cache: dict[cache_key, cache_value] = {}
        self.compilation_unit_to_cache_keys: dict[compilation_unit_fqn, set[cache_key]] = {}

    def get(self, compilation_unit_fqn: compilation_unit_fqn, symbol_name: symbol_name) -> cache_value | None:
        key: cache_key = (compilation_unit_fqn, symbol_name)
        return self.cache.get(key)

    def set(self, compilation_unit_fqn: compilation_unit_fqn, symbol_name: symbol_name, resolved_ids, unresolved_ids) -> None:
        key: cache_key = (compilation_unit_fqn, symbol_name)
        self.cache[key] = (set(resolved_ids), set(unresolved_ids))
        if compilation_unit_fqn not in self.compilation_unit_to_cache_keys:
            self.compilation_unit_to_cache_keys[compilation_unit_fqn] = set()
        self.compilation_unit_to_cache_keys[compilation_unit_fqn].add(key)

    def clear(self) -> None:
        self.cache.clear()
        self.compilation_unit_to_cache_keys.clear()

    def clear_compilation_unit(self, compilation_unit_fqn: compilation_unit_fqn) -> None:
        keys = self.compilation_unit_to_cache_keys.pop(compilation_unit_fqn, set())
        for key in keys:
            self.cache.pop(key, None)
