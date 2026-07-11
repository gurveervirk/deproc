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
import logging

logger = logging.getLogger(__name__)

def _get_symbol(symbol_id: SymbolID, context: Context):
    symbol = context.entity_registry.get(symbol_id)
    if not symbol:
        logger.warning(f"Symbol not found for ID: {symbol_id}")
        return None
    return symbol

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
