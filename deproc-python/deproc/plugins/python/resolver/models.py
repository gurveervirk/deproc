from dataclasses import dataclass
from deproc.core.interfaces.parser.models import SymbolID

type ResolvedIDs = set[SymbolID]
type UnresolvedIDs = set[SymbolID]

@dataclass
class PythonResolverResult:
    resolved_ids: ResolvedIDs
    unresolved_ids: UnresolvedIDs