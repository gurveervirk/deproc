from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

class Docstring(BaseModel):
    """
    Represents a generic language-agnostic docstring metadata model.
    """
    docstring_start_line: int | None = None
    docstring_end_line: int | None = None

class Signature(BaseModel):
    signature_start_line: int | None = None
    signature_end_line: int | None = None

class SourceRange(BaseModel):
    lineno: int | None = None
    end_lineno: int | None = None
    col_offset: int | None = None
    end_col_offset: int | None = None

class Annotation(BaseModel):
    name: str
    line_start: int | None = None
    line_end: int | None = None

class ImportStmt(SourceRange):
    type: str

class Argument(BaseModel):
    name: str | None = None
    default_value: str | None = None
    type_annotation: str | None = None

class FunctionLike(Docstring, Signature, SourceRange):
    name: str
    type: str = "FUNCTION"

class Variable(SourceRange):
    name: str
    value: str | None = None
    type_annotation: str | None = None

class TypeDefinition(Docstring, Signature, SourceRange):
    name: str
    type: str = "TYPE_DEFINITION"
    kind: str
    annotations: list[Annotation] = Field(default_factory=list)
    inherits: list[str] = Field(default_factory=list)
    methods: list[FunctionLike] = Field(default_factory=list)
    inner_type_definitions: list[TypeDefinition] = Field(default_factory=list)
    properties: list[Variable] = Field(default_factory=list)
    visibility: str | None = None

class ConditionalBlock(BaseModel):
    condition: str
    branch: str
    parent_block_start_line: int | None = None
    imports: list[ImportStmt] = Field(default_factory=list)
    type_definitions: list[TypeDefinition] = Field(default_factory=list)
    functions: list[FunctionLike] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    nested_blocks: list["ConditionalBlock"] = Field(default_factory=list)

class SourceFile(Docstring):
    file_path: str
    module_name: str
    imports: list[ImportStmt] = Field(default_factory=list)
    type_definitions: list[TypeDefinition] = Field(default_factory=list)
    functions: list[FunctionLike] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    conditional_blocks: list[ConditionalBlock] = Field(default_factory=list)
    source_bytes: bytes
    source: str