from dataclasses import dataclass

@dataclass(kw_only=True)
class SymbolTable:
    language: str

__all__ = ["SymbolTable"]