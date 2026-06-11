from dataclasses import dataclass

@dataclass
class PythonModuleSymbolMap:
    symbol_map: dict[str, list[str]]

@dataclass
class PythonSymbolTable:
    module_symbol_maps: dict[str, PythonModuleSymbolMap]