from deproc_core.deproc.core.context import Context
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

def _get_symbol(symbol_id: str, context: Context):
    symbol = context.entity_registry.get(symbol_id)
    if not symbol:
        return None
    return symbol

def resolve_symbol(data_in: PythonResolverInput, context: Context) -> list[str]:
    symbol_table: PythonSymbolTable = context.get_symbol_table("python")
    if not symbol_table:
        return []
    
    module_fqn = data_in.module_fqn
    symbol_name = data_in.symbol_name

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
                alias_ids.add(symbol_id)
    
    if alias_ids:
        resolved_alias_ids = resolve_alias_ids(alias_ids, context)
        resolved_ids.update(resolved_alias_ids)
    
    return list(resolved_ids)

def resolve_alias_ids(alias_ids: set[str], context: Context) -> set[str]:
    if not alias_ids:
        return set()
    
    resolved_ids = set()
    for symbol_id in alias_ids:
        symbol = _get_symbol(symbol_id, context)
        if isinstance(symbol, PythonImportAlias):
            resolved_ids_from_alias = resolve_alias(symbol, context)
            resolved_ids.update(resolved_ids_from_alias)
        else:
            resolved_ids.add(symbol_id)

    return resolved_ids

def resolve_alias(alias: PythonImportAlias, context: Context) -> list[SymbolID]:
    import_statement_id = alias.parent_id
    module = get_module(import_statement_id, context)
    module_fqn = module.fqn if module else None

    symbol_table: PythonSymbolTable = context.get_symbol_table("python")
    if not symbol_table:
        return []
    
    module_symbol_map: PythonModuleSymbolMap = symbol_table.module_symbol_maps.get(module_fqn, None)
    if module_symbol_map is None:
        return []
    
    import_name = alias.name
    resolved_ids = module_symbol_map.get(import_name, [])
    return resolved_ids

def get_module(symbol_id: str, context: Context) -> PythonModule | None:
    symbol = _get_symbol(symbol_id, context)
    if not symbol:
        return None
    
    if isinstance(symbol, PythonModule):
        return symbol
    
    parent_id = getattr(symbol, "parent_id", None)
    if not parent_id:
        return None
    
    return get_module(parent_id, context)