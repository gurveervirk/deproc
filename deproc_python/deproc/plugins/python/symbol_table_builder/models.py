from dataclasses import dataclass
from deproc.core.interfaces.symbol_table_builder.models import SymbolTable

@dataclass
class PythonModuleSymbolMap:
    symbol_map: dict[str, list[str]]

@dataclass(kw_only=True)
class PythonSymbolTable(SymbolTable):
    language: str = "python"
    module_symbol_maps: dict[str, PythonModuleSymbolMap]