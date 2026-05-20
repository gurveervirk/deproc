from dataclasses import dataclass

@dataclass
class AliasMapping:
    fqn: str
    aliases: list[str]

@dataclass
class AliasFinderResult:
    alias_mappings: list[AliasMapping]