from dataclasses import dataclass, field

from deproc.core.interfaces.parser.models import SymbolID
from deproc.core.interfaces.resolver import ResolutionStatus

type ResolvedIDs = set[SymbolID]
type UnresolvedIDs = set[SymbolID]


@dataclass
class PythonResolverResult:
    resolved_ids: ResolvedIDs
    unresolved_ids: UnresolvedIDs
    ambiguous_ids: set[SymbolID] = field(default_factory=set)
    inaccessible_ids: set[SymbolID] = field(default_factory=set)
    reason: str | None = None

    @property
    def status(self) -> ResolutionStatus:
        if self.ambiguous_ids:
            return ResolutionStatus.AMBIGUOUS
        if self.resolved_ids:
            return ResolutionStatus.RESOLVED
        if self.inaccessible_ids:
            return ResolutionStatus.INACCESSIBLE
        return ResolutionStatus.UNRESOLVED

    @property
    def candidates(self) -> tuple[SymbolID, ...]:
        return tuple(
            sorted(self.ambiguous_ids or self.resolved_ids or self.inaccessible_ids)
        )
