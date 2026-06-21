from ..resolver.models import (
    ResolvedIDs as ResolvedIDs,
    UnresolvedIDs as UnresolvedIDs,
)

type module_fqn = str
type symbol_name = str

type cache_key = tuple[module_fqn, symbol_name]
type cache_value = tuple[ResolvedIDs, UnresolvedIDs]