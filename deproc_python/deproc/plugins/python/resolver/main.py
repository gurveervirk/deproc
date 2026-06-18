from deproc.core.interfaces.resolver import Resolver
from deproc.core.context import Context
from .models import PythonResolverInput
from .utils import resolve_symbol

class PythonResolver(Resolver[PythonResolverInput, list[str]]):
    def resolve(self, data_in: PythonResolverInput, context: Context) -> list[str]:
        return resolve_symbol(data_in, context)