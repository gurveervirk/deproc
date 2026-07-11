from deproc.core.interfaces.resolver import Resolver
from deproc.core.context import Context
from .models import (
    PythonResolverResult
)
from .utils import (
    _extract_alias_ids,
    _get_symbol,
    _get_target_module_fqn
)
from .models import (
    ResolvedIDs,
    UnresolvedIDs
)
from ..symbol_cache import PythonSymbolCache
from ..parser.models import (
    PythonImportAlias,
    SymbolID,
)
import logging

logger = logging.getLogger(__name__)

class PythonResolver(Resolver[PythonResolverResult]):
    def _populate_cache(
        self,
        module_fqn: str,
        symbol_name: str,
        resolved_ids: list[SymbolID],
        unresolved_ids: list[SymbolID],
        cache: PythonSymbolCache
    ):
        if cache:
            cache.set(module_fqn, symbol_name, resolved_ids, unresolved_ids)

    def _populate_module_cache_key_maps(
        self,
        module_fqn: str,
        cache_keys: set[tuple[str, str]],
        cache: PythonSymbolCache
    ):
        if cache:
            cache.add_cache_keys_for_module(module_fqn, cache_keys)

    def _populate_module_cache_key_maps_for_cached_result(
        self,
        module_fqn: str,
        symbol_name: str,
        cache_keys: set[tuple[str, str]],
        cache: PythonSymbolCache
    ):
        if not cache_keys:
            return
        
        current_cache_key = (module_fqn, symbol_name)
        module_fqns = cache.get_modules_for_cache_key(current_cache_key)

        for cache_key in cache_keys:
            cache.add_modules_for_cache_key(cache_key, module_fqns)

    def get_ids_by_fqn(
        self,
        module_fqn: str,
        symbol_name: str,
        context: Context
    ) -> set[SymbolID]:
        return context.entity_registry.get_ids_by_fqn(f"{module_fqn}.{symbol_name}")
    
    def resolve_symbol(
        self,
        module_fqn: str,
        symbol_name: str,
        context: Context,
        visited: set[SymbolID] | None = None,
        cache_keys: set[tuple[str, str]] | None = None
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        symbol_cache: PythonSymbolCache = context.get_symbol_cache("python")
        if symbol_cache:
            cached_result = symbol_cache.get(module_fqn, symbol_name)
            if cached_result is not None:
                self._populate_module_cache_key_maps_for_cached_result(module_fqn, symbol_name, cache_keys, symbol_cache)
                return cached_result
        
        resolved_ids = self.get_ids_by_fqn(module_fqn, symbol_name, context)
        if not resolved_ids:
            logger.warning(f"Symbols not found for module: {module_fqn}, symbol: {symbol_name}, caching empty sets")
            self._populate_cache(module_fqn, symbol_name, set(), set(), symbol_cache)
            self._populate_module_cache_key_maps(module_fqn, cache_keys or set(), symbol_cache)
            return set(), set()

        found_alias_ids, resolved_ids = _extract_alias_ids(resolved_ids, context)
        unresolved_ids = set()

        if cache_keys is None:
            cache_keys = set()
        cache_keys.add((module_fqn, symbol_name))
        
        if found_alias_ids:
            resolved_alias_ids, unresolved_ids = self.resolve_alias_ids(found_alias_ids, context, visited, cache_keys)
            resolved_ids.update(resolved_alias_ids)
        
        self._populate_cache(module_fqn, symbol_name, resolved_ids, unresolved_ids, symbol_cache)
        self._populate_module_cache_key_maps(module_fqn, cache_keys, symbol_cache)

        return resolved_ids, unresolved_ids

    def resolve_alias_ids(
        self,
        alias_ids: set[SymbolID], 
        context: Context,
        visited: set[SymbolID] | None = None,
        cache_keys: set[tuple[str, str]] | None = None
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        if visited is None:
            visited = set()

        if not alias_ids:
            return set(), set()
        
        resolved_ids = set()
        unresolved_ids = set()
        for symbol_id in alias_ids:
            # Handle worst case circular import scenario explicitly
            if symbol_id in visited:
                continue
            visited.add(symbol_id)

            symbol = _get_symbol(symbol_id, context)
            if isinstance(symbol, PythonImportAlias):
                resolved_ids_from_alias, unresolved_ids_from_alias = self.resolve_alias(symbol, context, visited, cache_keys)
                if resolved_ids_from_alias:
                    resolved_ids.update(resolved_ids_from_alias)
                    unresolved_ids.update(unresolved_ids_from_alias)
                else:
                    unresolved_ids.add(symbol_id)
            else:
                resolved_ids.add(symbol_id)

        return resolved_ids, unresolved_ids

    def resolve_alias(
        self,
        alias: PythonImportAlias,
        context: Context,
        visited: set[SymbolID] | None = None,
        cache_keys: set[tuple[str, str]] | None = None
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        import_statement_id = alias.parent_id

        import_name = alias.name
        target_module_path = _get_target_module_fqn(import_statement_id, context)

        if not target_module_path:
            logger.warning(f"Target module path not found for alias: {alias.name}")
            return set(), set()

        return self.resolve_symbol(target_module_path, import_name, context, visited, cache_keys)

    def resolve(self, module_fqn: str, symbol_name: str, context: Context) -> PythonResolverResult:
        resolved_ids, unresolved_ids = self.resolve_symbol(module_fqn, symbol_name, context)
        return PythonResolverResult(resolved_ids=resolved_ids, unresolved_ids=unresolved_ids)