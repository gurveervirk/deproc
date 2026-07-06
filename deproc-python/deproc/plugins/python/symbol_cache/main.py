from deproc.core.interfaces.symbol_cache import SymbolCache
from .models import (
    cache_key,
    cache_value,
    module_fqn,
    symbol_name,
    ResolvedIDs,
    UnresolvedIDs
)

class PythonSymbolCache(SymbolCache[cache_key, cache_value]):
    def __init__(self):
        self.language = "python"
        self.cache: dict[cache_key, cache_value] = {}
        self.module_to_cache_keys: dict[module_fqn, set[cache_key]] = {}
        self.cache_key_to_modules: dict[cache_key, set[module_fqn]] = {}

    def get(self, module_fqn: module_fqn, symbol_name: symbol_name) -> cache_value | None:
        key: cache_key = (module_fqn, symbol_name)
        return self.cache.get(key)
    
    def set(self, module_fqn: module_fqn, symbol_name: symbol_name, resolved_ids: ResolvedIDs, unresolved_ids: UnresolvedIDs) -> None:
        key: cache_key = (module_fqn, symbol_name)
        self.cache[key] = (resolved_ids, unresolved_ids)

    def _link(self, module_fqn: module_fqn, key: cache_key) -> None:
        if module_fqn not in self.module_to_cache_keys:
            self.module_to_cache_keys[module_fqn] = set()
        self.module_to_cache_keys[module_fqn].add(key)

        if key not in self.cache_key_to_modules:
            self.cache_key_to_modules[key] = set()
        self.cache_key_to_modules[key].add(module_fqn)

    def add_cache_keys_for_module(self, module_fqn: module_fqn, keys: set[cache_key]) -> None:
        for key in keys:
            self._link(module_fqn, key)
    
    def get_cache_keys_for_module(self, module_fqn: module_fqn) -> set[cache_key]:
        return self.module_to_cache_keys.get(module_fqn, set())
    
    def add_modules_for_cache_key(self, key: cache_key, modules: set[module_fqn]) -> None:
        for module_fqn in modules:
            self._link(module_fqn, key)
    
    def get_modules_for_cache_key(self, key: cache_key) -> set[module_fqn]:
        return self.cache_key_to_modules.get(key, set())

    def clear(self) -> None:
        self.cache.clear()
        self.module_to_cache_keys.clear()
        self.cache_key_to_modules.clear()

    def clear_module(self, module_fqn: module_fqn) -> None:
        if module_fqn in self.module_to_cache_keys:
            for key in self.module_to_cache_keys[module_fqn]:
                if key in self.cache:
                    del self.cache[key]
                if key in self.cache_key_to_modules:
                    self.cache_key_to_modules[key].discard(module_fqn)
                    if not self.cache_key_to_modules[key]:
                        del self.cache_key_to_modules[key]
            del self.module_to_cache_keys[module_fqn]