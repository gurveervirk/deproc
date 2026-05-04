from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class Docstring:
    """
    Represents a generic language-agnostic docstring metadata model.
    """
    docstring_start_line: int | None = None
    docstring_end_line: int | None = None

@dataclass
class Signature:
    signature_start_line: int | None = None
    signature_end_line: int | None = None

@dataclass
class SourceRange:
    lineno: int | None = None
    end_lineno: int | None = None
    col_offset: int | None = None
    end_col_offset: int | None = None

@dataclass
class Annotation:
    name: str
    line_start: int | None = None
    line_end: int | None = None

@dataclass
class ImportStmt(SourceRange):
    type: str

@dataclass
class Argument(SourceRange):
    name: str | None = None
    default_value: str | None = None
    type_annotation: str | None = None

@dataclass
class FunctionLike(Docstring, Signature, SourceRange):
    name: str
    type: str = "FUNCTION"

@dataclass
class Variable(SourceRange):
    name: str
    value: str | None = None
    type_annotation: str | None = None

@dataclass
class TypeDefinition(Docstring, Signature, SourceRange):
    name: str
    type: str = "TYPE_DEFINITION"
    kind: str
    annotations: list[Annotation] = field(default_factory=list)
    inherits: list[str] = field(default_factory=list)
    methods: list[FunctionLike] = field(default_factory=list)
    inner_type_definitions: list[TypeDefinition] = field(default_factory=list)
    properties: list[Variable] = field(default_factory=list)
    visibility: str | None = None

@dataclass
class ConditionalBlock:
    condition: str
    branch: str
    parent_block_start_line: int | None = None
    imports: list[ImportStmt] = field(default_factory=list)
    type_definitions: list[TypeDefinition] = field(default_factory=list)
    functions: list[FunctionLike] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    nested_blocks: list["ConditionalBlock"] = field(default_factory=list)

@dataclass
class SourceFile(Docstring):
    file_path: str
    module_name: str
    imports: list[ImportStmt] = field(default_factory=list)
    type_definitions: list[TypeDefinition] = field(default_factory=list)
    functions: list[FunctionLike] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    conditional_blocks: list[ConditionalBlock] = field(default_factory=list)
    source_bytes: bytes
    source: str