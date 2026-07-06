from deproc.core.context import Context
from .models import (
    ResolvedIDs,
    UnresolvedIDs
)
from ..parser.models import (
    PythonImportAlias,
    SymbolID
)
from ..linker.models import PythonModule
from ..symbol_table_builder.models import (
    PythonSymbolTable,
    PythonModuleSymbolMap
)
from ..symbol_cache import PythonSymbolCache
import logging

logger = logging.getLogger(__name__)

def _get_symbol(symbol_id: SymbolID, context: Context):
    symbol = context.entity_registry.get(symbol_id)
    if not symbol:
        logger.warning(f"Symbol not found for ID: {symbol_id}")
        return None
    return symbol

def _populate_cache(module_fqn: str, symbol_name: str, resolved_ids: list[SymbolID], unresolved_ids: list[SymbolID], cache: PythonSymbolCache):
    if cache:
        cache.set(module_fqn, symbol_name, resolved_ids, unresolved_ids)

def _populate_module_cache_key_maps(module_fqn: str, cache_keys: set[tuple[str, str]], cache: PythonSymbolCache):
    if cache:
        cache.add_cache_keys_for_module(module_fqn, cache_keys)

def _populate_module_cache_key_maps_for_cached_result(module_fqn: str, symbol_name: str, cache_keys: set[tuple[str, str]], cache: PythonSymbolCache):
    current_cache_key = (module_fqn, symbol_name)
    module_fqns = cache.get_modules_for_cache_key(current_cache_key)

    for cache_key in cache_keys:
        cache.add_modules_for_cache_key(cache_key, module_fqns)

def _get_module(symbol_id: SymbolID, context: Context) -> PythonModule | None:
    symbol = _get_symbol(symbol_id, context)
    if not symbol:
        return None
    
    if isinstance(symbol, PythonModule):
        return symbol
    
    parent_id = getattr(symbol, "parent_id", None)
    if not parent_id:
        return None
    
    return _get_module(parent_id, context)

def _get_target_module_fqn(import_statement_id: SymbolID, context: Context) -> str | None:
    import_statement = _get_symbol(import_statement_id, context)
    if not import_statement:
        return None
    
    path = getattr(import_statement, "path", None)

    # Handle relative imports
    if path and path.startswith("."):
        parent_module = _get_module(import_statement_id, context)
        if parent_module:
            parent_fqn = parent_module.fqn
            if parent_fqn:
                # Resolve relative path to absolute FQN
                relative_parts = path.split(".")
                parent_parts = parent_fqn.split(".")
                # Remove the last part of the parent FQN for each leading dot in the relative path
                while relative_parts and relative_parts[0] == "":
                    relative_parts.pop(0)
                    if parent_parts:
                        parent_parts.pop()
                # Combine the remaining parts to form the target FQN
                target_fqn = ".".join(parent_parts + relative_parts)
                return target_fqn

    return path

def _extract_alias_ids(symbol_ids: set[SymbolID], context: Context) -> tuple[ResolvedIDs, UnresolvedIDs]:
    alias_ids = set()
    non_alias_ids = set()

    for symbol_id in symbol_ids:
        symbol = _get_symbol(symbol_id, context)
        if isinstance(symbol, PythonImportAlias):
            alias_ids.add(symbol_id)
        else:
            non_alias_ids.add(symbol_id)

    return alias_ids, non_alias_ids

def resolve_symbol(
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
            _populate_module_cache_key_maps_for_cached_result(module_fqn, symbol_name, cache_keys, symbol_cache)
            return cached_result
    
    symbol_table: PythonSymbolTable = context.get_symbol_table("python")
    if not symbol_table:
        logger.warning(f"Symbol table not found for python, caching empty sets for ({module_fqn}, {symbol_name})")
        _populate_cache(module_fqn, symbol_name, set(), set(), symbol_cache)
        return set(), set()

    module_symbol_map: PythonModuleSymbolMap = symbol_table.module_symbol_maps.get(module_fqn, None)
    if module_symbol_map is None:
        logger.warning(f"Module symbol map not found for module: {module_fqn}, caching empty sets for ({module_fqn}, {symbol_name})")
        _populate_cache(module_fqn, symbol_name, set(), set(), symbol_cache)
        return set(), set()
    
    resolved_ids = set(module_symbol_map.get(symbol_name, []))
    if not resolved_ids:
        logger.warning(f"Symbols not found for module: {module_fqn}, symbol: {symbol_name}, caching empty sets for ({module_fqn}, {symbol_name})")
        _populate_cache(module_fqn, symbol_name, set(), set(), symbol_cache)
        return set(), set()

    alias_ids, resolved_ids = _extract_alias_ids(resolved_ids, context)
    unresolved_ids = set()

    if cache_keys is None:
        cache_keys = set()
    cache_keys.add((module_fqn, symbol_name))
    
    if alias_ids:
        resolved_alias_ids, unresolved_ids = resolve_alias_ids(alias_ids, context, visited)
        resolved_ids.update(resolved_alias_ids)
    
    _populate_cache(module_fqn, symbol_name, resolved_ids, unresolved_ids, symbol_cache)
    _populate_module_cache_key_maps(module_fqn, cache_keys, symbol_cache)

    return resolved_ids, unresolved_ids

def resolve_alias_ids(
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
            resolved_ids_from_alias, unresolved_ids_from_alias = resolve_alias(symbol, context, visited, cache_keys)
            if resolved_ids_from_alias:
                resolved_ids.update(resolved_ids_from_alias)
                unresolved_ids.update(unresolved_ids_from_alias)
            else:
                unresolved_ids.add(symbol_id)
        else:
            resolved_ids.add(symbol_id)

    return resolved_ids, unresolved_ids

def resolve_alias(
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

    return resolve_symbol(target_module_path, import_name, context, visited, cache_keys)