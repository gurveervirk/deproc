"""
Provisional data models for the parser interface.
Please use these models either directly in the plugin implementations or as a reference for defining plugin-specific models.
"""
from dataclasses import dataclass, field

@dataclass
class SourceRange:
    lineno: int
    end_lineno: int
    col_offset: int
    end_col_offset: int

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
class ImportStmt:
    source_range: SourceRange
    type: str

@dataclass
class Argument:
    name: str
    source_range: SourceRange
    default_value: str | None
    type_annotation: str | None

@dataclass(kw_only=True)
class FunctionLike(Docstring):
    name: str
    source_range: SourceRange
    type: str = field(default="FUNCTION")
    signature: Signature

@dataclass
class VariableBinding:
    name: str
    source_range: SourceRange
    is_destructuring: bool = False

@dataclass
class VariableDeclaration:
    bindings: list[VariableBinding]
    source_range: SourceRange
    value_range: SourceRange | None
    type_annotation: str | None
    modifiers: list[str] = field(default_factory=list)

@dataclass
class Property:
    name: str
    source_range: SourceRange
    type_annotation: str | None
    default_value_range: SourceRange | None
    modifiers: list[str] = field(default_factory=list)

@dataclass(kw_only=True)
class TypeDefinition(Docstring):
    name: str
    source_range: SourceRange
    type: str = field(default="TYPE_DEFINITION")
    annotations: list[Annotation] = field(default_factory=list)
    inherits: list[str] = field(default_factory=list)
    methods: list[FunctionLike] = field(default_factory=list)
    inner_type_definitions: list["TypeDefinition"] = field(default_factory=list)
    properties: list[Property] = field(default_factory=list)
    visibility: str | None

@dataclass
class ConditionalBlock:
    condition: str
    branch: str
    parent_block_start_line: int | None
    imports: list[ImportStmt] = field(default_factory=list)
    type_definitions: list[TypeDefinition] = field(default_factory=list)
    functions: list[FunctionLike] = field(default_factory=list)
    variables: list[VariableDeclaration] = field(default_factory=list)
    nested_blocks: list["ConditionalBlock"] = field(default_factory=list)

@dataclass(kw_only=True)
class SourceFile(Docstring):
    file_path: str
    module_name: str
    imports: list[ImportStmt] = field(default_factory=list)
    type_definitions: list[TypeDefinition] = field(default_factory=list)
    functions: list[FunctionLike] = field(default_factory=list)
    variables: list[VariableDeclaration] = field(default_factory=list)
    conditional_blocks: list[ConditionalBlock] = field(default_factory=list)
    source_bytes: bytes
    source: str