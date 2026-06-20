from dataclasses import dataclass
from deproc.core.interfaces.symbol_table_builder.models import SymbolTable
from deproc.core.interfaces.parser.models import SymbolID

type PythonModuleSymbolMap = dict[str, set[SymbolID]]

@dataclass(kw_only=True)
class PythonSymbolTable(SymbolTable):
    language: str = "python"
    module_symbol_maps: dict[str, PythonModuleSymbolMap]