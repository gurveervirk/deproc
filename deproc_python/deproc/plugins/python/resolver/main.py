from deproc_core.deproc.core.interfaces.resolver import Resolver
from deproc_core.deproc.core.context import Context
from .models import PythonResolverInput
from .utils import resolve_symbol
from ..symbol_table_builder.models import PythonSymbolTable

class PythonResolver(Resolver[PythonSymbolTable[PythonResolverInput], list[str]]):
    def resolve(self, data_in: PythonResolverInput, context: Context) -> list[str]:
        return resolve_symbol(data_in, context)