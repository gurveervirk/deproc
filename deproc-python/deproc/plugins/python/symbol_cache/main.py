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

    def get(self, module_fqn: module_fqn, symbol_name: symbol_name) -> cache_value | None:
        key: cache_key = (module_fqn, symbol_name)
        return self.cache.get(key)
    
    def set(self, module_fqn: module_fqn, symbol_name: symbol_name, resolved_ids: ResolvedIDs, unresolved_ids: UnresolvedIDs) -> None:
        key: cache_key = (module_fqn, symbol_name)
        self.cache[key] = (resolved_ids, unresolved_ids)

    def clear(self) -> None:
        self.cache.clear()
        self.module_to_cache_keys.clear()

    def clear_module(self, module_fqn: module_fqn) -> None:
        if module_fqn in self.module_to_cache_keys:
            for key in self.module_to_cache_keys[module_fqn]:
                if key in self.cache:
                    del self.cache[key]
            del self.module_to_cache_keys[module_fqn]