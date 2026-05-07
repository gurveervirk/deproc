from dataclasses import dataclass

@dataclass
class AliasMapping:
    entity_name: str
    aliases: list[str]

@dataclass
class AliasFinderResult:
    alias_mappings: list[AliasMapping]