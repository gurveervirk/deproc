from deproc.core.interfaces.resolver import Resolver
from deproc.core.context import Context
from .models import (
    PythonResolverResult
)
from .utils import resolve_symbol

class PythonResolver(Resolver[PythonResolverResult]):
    def resolve(self, module_fqn: str, symbol_name: str, context: Context) -> PythonResolverResult:
        resolved_ids, unresolved_ids = resolve_symbol(module_fqn, symbol_name, context)
        return PythonResolverResult(resolved_ids=resolved_ids, unresolved_ids=unresolved_ids)