from dataclasses import dataclass, field

from deproc.core.interfaces.parser.models import SymbolID

type ResolvedIDs = set[SymbolID]
type UnresolvedIDs = set[SymbolID]
type InaccessibleIDs = set[SymbolID]


@dataclass
class JavaResolverResult:
    resolved_ids: ResolvedIDs
    unresolved_ids: UnresolvedIDs
    inaccessible_ids: InaccessibleIDs = field(default_factory=set)
