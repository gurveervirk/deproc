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

    def get(self, module_fqn: module_fqn, symbol_name: symbol_name) -> cache_value | None:
        key: cache_key = (module_fqn, symbol_name)
        return self.cache.get(key)
    
    def set(self, module_fqn: module_fqn, symbol_name: symbol_name, resolved_ids: ResolvedIDs, unresolved_ids: UnresolvedIDs) -> None:
        key: cache_key = (module_fqn, symbol_name)
        self.cache[key] = (resolved_ids, unresolved_ids)

    def clear(self) -> None:
        self.cache.clear()