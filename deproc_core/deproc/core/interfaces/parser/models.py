"""
Provisional data models for the parser interface.
Please use these models either directly in the plugin implementations or as a reference for defining plugin-specific models.
"""
from dataclasses import dataclass, field

@dataclass
class Docstring:
    """
    Represents a generic language-agnostic docstring metadata model.
    """
    docstring_start_line: int
    docstring_end_line: int

@dataclass
class Signature:
    signature_start_line: int
    signature_end_line: int

@dataclass
class SourceRange:
    lineno: int
    end_lineno: int
    col_offset: int
    end_col_offset: int

@dataclass
class Annotation:
    name: str
    lineno: int | None
    end_lineno: int | None

@dataclass
class ImportStmt(SourceRange):
    type: str

@dataclass
class Argument(SourceRange):
    name: str
    default_value: str | None
    type_annotation: str | None

@dataclass(kw_only=True)
class FunctionLike(Docstring, Signature, SourceRange):
    name: str
    type: str = field(default="FUNCTION")

@dataclass
class Variable(SourceRange):
    name: str
    value: str | None
    type_annotation: str | None

@dataclass(kw_only=True)
class TypeDefinition(Docstring, Signature, SourceRange):
    name: str
    type: str = field(default="TYPE_DEFINITION")
    kind: str
    annotations: list[Annotation] = field(default_factory=list)
    inherits: list[str] = field(default_factory=list)
    methods: list[FunctionLike] = field(default_factory=list)
    inner_type_definitions: list["TypeDefinition"] = field(default_factory=list)
    properties: list[Variable] = field(default_factory=list)
    visibility: str | None

@dataclass
class ConditionalBlock:
    condition: str
    branch: str
    parent_block_start_line: int | None
    imports: list[ImportStmt] = field(default_factory=list)
    type_definitions: list[TypeDefinition] = field(default_factory=list)
    functions: list[FunctionLike] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    nested_blocks: list["ConditionalBlock"] = field(default_factory=list)

@dataclass(kw_only=True)
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