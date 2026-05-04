from typing_extensions import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field, ConfigDict
import hashlib
import re


class ExternalEntityRef(BaseModel):
    """
    Reference to an external entity (outside current module being processed).
    Used for INHERITS/IMPORTS relations where the target may not be tracked.
    """
    name: str
    type: str = "UNKNOWN"
    version: Optional[str] = None
    content_hash: Optional[str] = None
    alias: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False

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


class Entity(BaseModel):
    """
    Module-agnostic entity class.
    """
    name: str
    type: str = "UNKNOWN"
    labels: List[str]
    properties: Dict
    content_hash: str
    language: str = "python"

    def __init__(self, name: str, labels: List[str], properties: Dict, content_hash: Optional[str] = None, type: str = "UNKNOWN", language: str = "python"):
        # Sanitize labels
        sanitized_labels = _sanitize_labels(labels)
        
        # Compute content_hash if not provided
        if content_hash is None:
            content_hash = _compute_content_hash(name, properties)
        
        super().__init__(name=name, labels=sanitized_labels, properties=properties, content_hash=content_hash, type=type, language=language)

    @property
    def label(self) -> str:
        """
        Backwards-compatible primary label accessor. Returns the first label if available.
        """
        return self.labels[0] if self.labels else ""

    def __repr__(self):
        return f"{self.label} ({self.name})"

class Relationship(BaseModel):
    """
    Module-agnostic relation class.
    """
    from_entity: Entity
    to_entity: Union[Entity, ExternalEntityRef]
    label: str
    properties: Dict | None

    def __init__(self, from_entity: Entity, to_entity: Union[Entity, ExternalEntityRef], label: str, properties: Dict):
        super().__init__(from_entity=from_entity, to_entity=to_entity, label=label, properties=properties)

    def __repr__(self):
        return f"{self.from_entity} --{self.label}--> {self.to_entity}"


class ExtractionResult(BaseModel):
    """
    Result of an extraction process containing entities, relationships, and other metadata.
    """
    entities: List[Entity]
    relations: List[Relationship]
    other_relations: Dict[str, List[Tuple[str, ExternalEntityRef]]]
    aliases: Dict[str, List[str]] = Field(default_factory=dict)
    symbol_maps: Dict[str, List["SymbolMapEntry"]] = Field(default_factory=dict)
    alias_hops: Dict[str, List["AliasHop"]] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SymbolMapEntry(BaseModel):
    name: str
    origin: str
    entity_fqn: Optional[str] = None
    source_fqn: Optional[str] = None
    condition: Optional[str] = None
    line_no: Optional[int] = None
    parent_block_start_line: Optional[int] = None
    is_reexport: bool = False


class AliasHop(BaseModel):
    module_fqn: str
    line_no: Optional[int] = None
    next_hop_fqn: str