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
class ImportStatement:
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
    fqn: str
    source_range: SourceRange
    type: str = field(default="FUNCTION")
    signature: Signature

@dataclass
class SimpleBinding:
    name: str

@dataclass
class ComplexBinding:
    source_range: SourceRange | None

@dataclass(kw_only=True)
class VariableDeclaration:
    fqn: str | None
    type: str = field(default="VARIABLE")
    source_range: SourceRange
    variable_binding: SimpleBinding | ComplexBinding
    value_range: SourceRange | None
    type_annotation: SourceRange | None
    modifiers: list[str] = field(default_factory=list)

@dataclass(kw_only=True)
class TypeDefinition(Docstring):
    name: str
    fqn: str
    source_range: SourceRange
    type: str = field(default="TYPE_DEFINITION")
    annotations: list[Annotation] = field(default_factory=list)
    inherits: list[str] = field(default_factory=list)
    methods: list[FunctionLike] = field(default_factory=list)
    inner_type_definitions: list["TypeDefinition"] = field(default_factory=list)
    properties: list[VariableDeclaration] = field(default_factory=list)
    visibility: str | None

@dataclass
class ControlFlowBlock:
    branch: str
    source_range: SourceRange
    condition_range: SourceRange | None
    import_statements: list[ImportStatement] = field(default_factory=list)
    type_definitions: list[TypeDefinition] = field(default_factory=list)
    functions: list[FunctionLike] = field(default_factory=list)
    variables: list[VariableDeclaration] = field(default_factory=list)
    nested_groups: list["ControlFlowGroup"] = field(default_factory=list)

@dataclass
class ControlFlowGroup:
    group_type: str
    source_range: SourceRange
    blocks: list[ControlFlowBlock] = field(default_factory=list)

@dataclass
class Node:
    path: str

@dataclass(kw_only=True)
class SourceFile(Docstring, Node):
    import_statements: list[ImportStatement] = field(default_factory=list)
    type_definitions: list[TypeDefinition] = field(default_factory=list)
    functions: list[FunctionLike] = field(default_factory=list)
    variables: list[VariableDeclaration] = field(default_factory=list)
    control_flow_groups: list[ControlFlowGroup] = field(default_factory=list)
    source: str