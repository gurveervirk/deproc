from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
import hashlib
import re

def _sanitize_labels(labels: List[str]) -> List[str]:
    """Sanitize labels by replacing invalid characters with underscores."""
    sanitized = []
    for label in labels:
        # Replace dots, colons, and other special chars with underscores
        clean_label = re.sub(r'[.:\-\s]+', '_', label)
        sanitized.append(clean_label)
    return sanitized

def _compute_content_hash(name: str, props: Dict) -> str:
    """
    Calculate content hash for an entity based on its name and all properties.
    Hashes all property keys and values in sorted order for deterministic results.
    """
    h = hashlib.sha256()
    
    # Include entity name
    h.update(name.encode("utf-8", errors="ignore"))
    h.update(b"|::|")
    
    # Hash all properties in sorted order for determinism
    for key in sorted(props.keys()):
        value = props[key]
        h.update(key.encode("utf-8", errors="ignore"))
        h.update(b"|::|")
        h.update(str(value).encode("utf-8", errors="ignore"))
        h.update(b"|::|")
    
    return h.hexdigest()

@dataclass
class ExternalEntityRef:
    """
    Reference to an external entity (outside current module being processed).
    Used for INHERITS/IMPORTS relations where the target may not be tracked.
    """
    name: str
    type: str = "UNKNOWN"
    version: Optional[str] = None
    content_hash: Optional[str] = None
    alias: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        if self.version:
            return f"{self.name}@{self.version}"
        return self.name

    def __hash__(self):
        """Make ExternalEntityRef hashable for use in sets. attributes is excluded (metadata)."""
        return hash((self.name, self.type, self.version, self.content_hash, self.alias))

    def __eq__(self, other):
        """Equality comparison for ExternalEntityRef. attributes is excluded (metadata)."""
        if not isinstance(other, ExternalEntityRef):
            return False
        return (self.name == other.name and
                self.type == other.type and
                self.version == other.version and
                self.content_hash == other.content_hash and
                self.alias == other.alias)

@dataclass
class Entity:
    """
    Module-agnostic entity class.
    """
    name: str
    labels: List[str]
    primary_label: Optional[str] = None
    properties: Dict[str, Any] | None = None
    type: str = "UNKNOWN"
    content_hash: Optional[str] = None
    language: str = "python"

    def __post_init__(self):
        self.labels = _sanitize_labels(self.labels)
        
        # Compute content_hash if not provided
        if self.content_hash is None:
            self.content_hash = _compute_content_hash(self.name, self.properties)

        if self.primary_label is None and self.labels:
            self.primary_label = self.labels[0]

    def __repr__(self):
        return f"{self.primary_label} ({self.name})"

@dataclass
class Relationship:
    """
    Module-agnostic relation class.
    """
    from_entity: Entity
    to_entity: Union[Entity, ExternalEntityRef]
    label: str
    properties: Dict[str, Any] | None = None

    def __repr__(self):
        return f"{self.from_entity} --{self.label}--> {self.to_entity}"

@dataclass
class SymbolMapEntry:
    name: str
    origin: str
    entity_fqn: Optional[str] = None
    source_fqn: Optional[str] = None
    condition: Optional[str] = None
    line_no: Optional[int] = None
    parent_block_start_line: Optional[int] = None
    is_reexport: bool = False

@dataclass
class AliasHop:
    module_fqn: str
    line_no: Optional[int] = None
    next_hop_fqn: str

@dataclass
class ExtractionResult:
    """
    Result of an extraction process containing entities, relationships, and other metadata.
    """
    entities: List[Entity]
    relations: List[Relationship]
    aliases: Dict[str, List[str]] = field(default_factory=dict)
    symbol_maps: Dict[str, List[SymbolMapEntry]] = field(default_factory=dict)
    alias_hops: Dict[str, List[AliasHop]] = field(default_factory=dict)
