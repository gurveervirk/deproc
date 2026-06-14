from dataclasses import dataclass

@dataclass
class PythonResolverInput:
    module_fqn: str
    symbol_name: str