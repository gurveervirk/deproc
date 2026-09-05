from dataclasses import dataclass, field

from deproc.core.interfaces.parser.models import SymbolID
from deproc.core.interfaces.resolver import ResolutionStatus

type ResolvedIDs = set[SymbolID]
type UnresolvedIDs = set[SymbolID]
type InaccessibleIDs = set[SymbolID]


@dataclass
class JavaResolverResult:
    resolved_ids: ResolvedIDs
    unresolved_ids: UnresolvedIDs
    inaccessible_ids: InaccessibleIDs = field(default_factory=set)
    ambiguous_ids: set[SymbolID] = field(default_factory=set)

    @property
    def status(self) -> ResolutionStatus:
        if self.ambiguous_ids:
            return ResolutionStatus.AMBIGUOUS
        if self.inaccessible_ids:
            return ResolutionStatus.INACCESSIBLE
        if self.resolved_ids:
            return ResolutionStatus.RESOLVED
        return ResolutionStatus.UNRESOLVED

    @property
    def candidates(self) -> tuple[SymbolID, ...]:
        return tuple(sorted(self.ambiguous_ids or self.resolved_ids))
