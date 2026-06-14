from deproc.core.context import Context
from deproc.core.interfaces.symbol_cache import SymbolCache
from .models import PythonResolverInput
from ..parser.models import (
    PythonImportAlias,
    SymbolID
)
from ..linker.models import PythonModule
from ..symbol_table_builder.models import (
    PythonSymbolTable,
    PythonModuleSymbolMap
)

def _get_symbol(symbol_id: SymbolID, context: Context):
    symbol = context.entity_registry.get(symbol_id)
    if not symbol:
        return None
    return symbol

def _populate_cache(module_fqn: str, symbol_name: str, resolved_ids: list[SymbolID], cache: SymbolCache):
    if cache:
        cache.set((module_fqn, symbol_name), resolved_ids)

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

def resolve_symbol(data_in: PythonResolverInput, context: Context) -> list[SymbolID]:
    symbol_table: PythonSymbolTable = context.get_symbol_table("python")
    if not symbol_table:
        return []
    
    module_fqn = data_in.module_fqn
    symbol_name = data_in.symbol_name

    symbol_cache = context.get_symbol_cache("python")
    if symbol_cache:
        cached_result = symbol_cache.get((module_fqn, symbol_name))
        if cached_result is not None:
            return cached_result

    module_symbol_map: PythonModuleSymbolMap = symbol_table.module_symbol_maps.get(module_fqn, None)
    if module_symbol_map is None:
        return []
    
    resolved_ids = set(module_symbol_map.get(symbol_name, []))
    if not resolved_ids:
        return []
    
    alias_ids = set()
    for symbol_id in resolved_ids:
            symbol = _get_symbol(symbol_id, context)
            if isinstance(symbol, PythonImportAlias):
                resolved_ids.discard(symbol_id)
                alias_ids.add(symbol_id)
    
    if alias_ids:
        resolved_alias_ids = resolve_alias_ids(alias_ids, symbol_cache, context)
        resolved_ids.update(resolved_alias_ids)
    
    _populate_cache(module_fqn, symbol_name, list(resolved_ids), symbol_cache)

    return list(resolved_ids)

def resolve_alias_ids(alias_ids: set[SymbolID], symbol_cache: SymbolCache, context: Context) -> set[SymbolID]:
    if not alias_ids:
        return set()
    
    resolved_ids = set()
    for symbol_id in alias_ids:
        symbol = _get_symbol(symbol_id, context)
        if isinstance(symbol, PythonImportAlias):
            resolved_ids_from_alias = resolve_alias(symbol, symbol_cache,context)
            resolved_ids.update(resolved_ids_from_alias)
        else:
            resolved_ids.add(symbol_id)

    return resolved_ids

def resolve_alias(alias: PythonImportAlias, symbol_cache: SymbolCache, context: Context) -> list[SymbolID]:
    import_statement_id = alias.parent_id

    import_name = alias.name
    target_module_path = _get_target_module_fqn(import_statement_id, context)

    if symbol_cache:
        cached_result = symbol_cache.get((target_module_path, import_name))
        if cached_result is not None:
            return cached_result

    symbol_table: PythonSymbolTable = context.get_symbol_table("python")
    if not symbol_table:
        return []
    
    module_symbol_map: PythonModuleSymbolMap = symbol_table.module_symbol_maps.get(target_module_path, None)
    if module_symbol_map is None:
        return []
    
    resolved_ids = module_symbol_map.get(import_name, [])

    alias_ids = set()
    for symbol_id in resolved_ids:
        symbol = _get_symbol(symbol_id, context)
        if isinstance(symbol, PythonImportAlias):
            alias_ids.add(symbol_id)
    
    if alias_ids:
        resolved_alias_ids = resolve_alias_ids(alias_ids, symbol_cache, context)
        resolved_ids.update(resolved_alias_ids)

    _populate_cache(target_module_path, import_name, list(resolved_ids), symbol_cache)

    return resolved_ids