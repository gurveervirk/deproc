from deproc.core.interfaces.symbol_cache import SymbolCache
from deproc.core.interfaces.parser.models import SymbolID
from .models import cache_key, module_fqn, symbol_name

class PythonSymbolCache(SymbolCache):
    def __init__(self):
        self.language = "python"
        self.cache: dict[cache_key, list[SymbolID]] = {}

    def get(self, module_fqn: module_fqn, symbol_name: symbol_name) -> list[SymbolID] | None:
        key: cache_key = (module_fqn, symbol_name)
        return self.cache.get(key)
    
    def set(self, module_fqn: module_fqn, symbol_name: symbol_name, symbol_ids: list[SymbolID]) -> None:
        key: cache_key = (module_fqn, symbol_name)
        self.cache[key] = symbol_ids