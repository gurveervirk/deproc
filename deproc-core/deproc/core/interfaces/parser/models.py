"""
Provisional data models for the parser interface.
Please use these models either directly in the plugin implementations or as a reference for defining plugin-specific models.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

type SymbolID = str


def generate_id() -> SymbolID:
    return uuid4().hex


@dataclass(kw_only=True)
class Entity:
    id: SymbolID = ""
    parent_id: str | None = None

    def __post_init__(self):
        if self.id:
            return
        self.id = self._compute_id()

    def _compute_id(self) -> str:
        """Use deterministic source identity when possible; otherwise allocate a transient ID.

        Persisted semantic entities must provide an explicit ID or override this
        method with deterministic identity inputs.
        """
        parent_id = getattr(self, "parent_id", None)
        source_range = getattr(self, "source_range", None)
        if parent_id and source_range:
            namespace = UUID(hex=parent_id)
            name = f"{type(self).__qualname__}:{source_range.lineno}:{source_range.end_lineno}:{source_range.col_offset}:{source_range.end_col_offset}"
            return uuid5(namespace, name).hex
        return uuid4().hex


@dataclass(kw_only=True)
class SourceRange:
    lineno: int
    end_lineno: int
    col_offset: int
    end_col_offset: int
    source_id: str | None = None


@dataclass
class Docstring:
    docstring_range: SourceRange | None


@dataclass
class Signature:
    signature_range: SourceRange
    arguments_range: SourceRange | None
    return_type_range: SourceRange | None


@dataclass
class Annotation:
    source_range: SourceRange
    name: str


@dataclass
class ImportStatement(Entity):
    source_range: SourceRange
    type: str


@dataclass(kw_only=True)
class FunctionLike(Docstring, Entity):
    name: str
    fqn: str
    source_range: SourceRange
    type: str = field(default="FUNCTION")
    signature: Signature | None = None


@dataclass
class SimpleBinding:
    name: str
    fqn: str


@dataclass
class ComplexBinding:
    source_range: SourceRange | None


@dataclass(kw_only=True)
class VariableDeclaration(Entity):
    type: str = field(default="VARIABLE")
    source_range: SourceRange
    variable_binding: SimpleBinding | ComplexBinding
    value_range: SourceRange | None
    type_annotation: SourceRange | None
    modifiers: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class TypeDefinition(Docstring, Entity):
    name: str
    fqn: str
    source_range: SourceRange
    type: str = field(default="TYPE_DEFINITION")
    annotations: list[Annotation] = field(default_factory=list)
    method_ids: list[str] = field(default_factory=list)
    inner_type_ids: list[str] = field(default_factory=list)
    property_ids: list[str] = field(default_factory=list)
    visibility: str | None


@dataclass
class ControlFlowBlock(Entity):
    branch: str
    source_range: SourceRange
    condition_range: SourceRange | None
    import_stmt_ids: list[SymbolID] = field(default_factory=list)
    type_ids: list[SymbolID] = field(default_factory=list)
    function_ids: list[SymbolID] = field(default_factory=list)
    variable_ids: list[SymbolID] = field(default_factory=list)
    nested_group_ids: list[SymbolID] = field(default_factory=list)


@dataclass
class ControlFlowGroup(Entity):
    group_type: str
    source_range: SourceRange
    block_ids: list[SymbolID] = field(default_factory=list)


@dataclass
class Node(Entity):
    path: str
    source_root_id: str | None = field(default=None, kw_only=True)

    def _compute_id(self) -> str:
        if self.source_root_id is None:
            identity = f"file://{self.path}"
        else:
            rooted_identity = json.dumps(
                [self.source_root_id, self.path],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            identity = f"file://rooted/{rooted_identity}"
        return uuid5(NAMESPACE_URL, identity).hex


@dataclass(kw_only=True)
class SemanticContainer(Entity):
    @property
    def semantic_type(self) -> str:
        return f"{type(self).__module__}.{type(self).__qualname__}"

    @property
    def semantic_key(self) -> str:
        fqn = getattr(self, "fqn", None)
        if not fqn:
            raise ValueError("Semantic containers require a non-empty FQN")
        return fqn

    @property
    def contribution_ids(self) -> list[SymbolID]:
        raise NotImplementedError

    def _compute_id(self) -> str:
        identity = json.dumps(
            [self.semantic_type, self.semantic_key],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return uuid5(NAMESPACE_URL, f"semantic://{identity}").hex

    def merge_from(self, other: SemanticContainer) -> None:
        if type(self) is not type(other) or self.semantic_key != other.semantic_key:
            raise ValueError("Only matching semantic containers can be merged")
        if self.parent_id and other.parent_id and self.parent_id != other.parent_id:
            raise ValueError("Matching semantic containers have conflicting parents")
        if self.parent_id is None:
            self.parent_id = other.parent_id
        self._merge_contributions(other)

    def _merge_contributions(self, other: SemanticContainer) -> None:
        raise NotImplementedError


@dataclass(kw_only=True)
class SourceFile(Docstring, Node):
    import_stmt_ids: list[SymbolID] = field(default_factory=list)
    type_ids: list[SymbolID] = field(default_factory=list)
    function_ids: list[SymbolID] = field(default_factory=list)
    variable_ids: list[SymbolID] = field(default_factory=list)
    control_flow_group_ids: list[SymbolID] = field(default_factory=list)
    source: str

    def _compute_id(self) -> str:
        h = hashlib.sha256(self.source.encode()).hexdigest()[:16]
        if self.source_root_id is None:
            identity = f"file://{self.path}#{h}"
        else:
            rooted_identity = json.dumps(
                [self.source_root_id, self.path, h],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            identity = f"file://rooted/{rooted_identity}"
        return uuid5(NAMESPACE_URL, identity).hex
