from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModifierFlags(BaseModel):
    is_public: bool = False
    is_private: bool = False
    is_protected: bool = False
    is_static: bool = False
    is_final: bool = False
    is_abstract: bool = False
    is_synchronized: bool = False
    is_native: bool = False
    is_default: bool = False
    is_strictfp: bool = False
    is_transient: bool = False
    is_volatile: bool = False
    is_sealed: bool = False
    is_non_sealed: bool = False


class Docstring(BaseModel):
    docstring: str | None = None
    docstring_start_line: int | None = None
    docstring_end_line: int | None = None


class Signature(BaseModel):
    signature_start_line: int | None = None
    signature_end_line: int | None = None


class SourceRange(BaseModel):
    lineno: int | None = None
    end_lineno: int | None = None
    source: str = ""


class DecoratorInfo(BaseModel):
    name: str
    line_start: int | None = None
    line_end: int | None = None


class RecordComponent(SourceRange):
    name: str
    type: str | None = None


class ImportStmt(BaseModel):
    type: str
    source: str
    lineno: int
    path: str | None = None
    is_static: bool = False
    is_wildcard: bool = False


class Parameter(BaseModel):
    name: str | None = None
    type: str | None = None
    modifiers: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    decorator_details: list[DecoratorInfo] = Field(default_factory=list)
    is_varargs: bool = False
    source: str = ""


class EnumConstant(SourceRange):
    name: str


class FunctionLike(Docstring, Signature, SourceRange):
    name: str
    type: str = "FUNCTION"
    decorators: list[str] = Field(default_factory=list)
    decorator_details: list[DecoratorInfo] = Field(default_factory=list)
    visibility: str | None = None
    args: str = ""
    return_type: str | None = None


class PythonFunctionLike(FunctionLike):
    pass


class JavaClassMethod(ModifierFlags, FunctionLike):
    modifiers: list[str] = Field(default_factory=list)
    is_constructor: bool = False
    throws: list[str] = Field(default_factory=list)
    type_parameters: str | None = None
    parameters: list[Parameter] = Field(default_factory=list)


class PythonVariable(SourceRange):
    name: str
    value: str | None = None
    operator: str | None = None
    type_annotation: str | None = None
    is_all_caps: bool = False
    is_augmented: bool = False
    is_type_alias: bool = False


class ClassVariable(ModifierFlags, Docstring, SourceRange):
    name: str
    value: str | None = None
    type_annotation: str | None = None
    is_all_caps: bool = False
    is_augmented: bool = False
    is_type_alias: bool = False
    declaration_kind: str | None = None
    annotations: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    decorator_details: list[DecoratorInfo] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)
    visibility: str | None = None


Variable = PythonVariable | ClassVariable


class Class(Docstring, Signature, SourceRange):
    name: str
    type: str = "CLASS"
    decorators: list[str] = Field(default_factory=list)
    decorator_details: list[DecoratorInfo] = Field(default_factory=list)
    bases: list[str] = Field(default_factory=list)
    methods: list[FunctionLike] = Field(default_factory=list)
    inner_classes: list["Class"] = Field(default_factory=list)
    class_variables: list[Variable] = Field(default_factory=list)
    visibility: str | None = None


class PythonClass(Class):
    methods: list[PythonFunctionLike] = Field(default_factory=list)
    inner_classes: list["PythonClass"] = Field(default_factory=list)
    class_variables: list[PythonVariable] = Field(default_factory=list)


class TypeDeclaration(ModifierFlags, Class):
    declaration_kind: str = "class"
    modifiers: list[str] = Field(default_factory=list)
    annotations: list[str] = Field(default_factory=list)
    extends: str | None = None
    implements: list[str] = Field(default_factory=list)
    type_parameters: str | None = None
    record_components: list[RecordComponent] | None = None
    enum_constants: list[EnumConstant] | None = None
    methods: list[JavaClassMethod] = Field(default_factory=list)
    inner_classes: list["TypeDeclaration"] = Field(default_factory=list)
    class_variables: list[ClassVariable] = Field(default_factory=list)


class ConditionalBlock(BaseModel):
    condition: str
    branch: str
    parent_block_start_line: int | None = None
    imports: list[ImportStmt] = Field(default_factory=list)
    classes: list[Class] = Field(default_factory=list)
    functions: list[FunctionLike] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    nested_blocks: list["ConditionalBlock"] = Field(default_factory=list)


class SourceFile(Docstring):
    file_path: str
    module_name: str
    imports: list[ImportStmt] = Field(default_factory=list)
    classes: list[Class] = Field(default_factory=list)
    functions: list[FunctionLike] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    conditional_blocks: list[ConditionalBlock] = Field(default_factory=list)
    source_bytes: bytes
    source: str


class ParsedPythonSourceFile(SourceFile):
    classes: list[PythonClass] = Field(default_factory=list)
    functions: list[PythonFunctionLike] = Field(default_factory=list)
    variables: list[PythonVariable] = Field(default_factory=list)


class ParsedJavaSourceFile(SourceFile):
    classes: list[TypeDeclaration] = Field(default_factory=list)
    functions: list[JavaClassMethod] = Field(default_factory=list)
    variables: list[ClassVariable] = Field(default_factory=list)
    package_name: str | None = None


class JavaScriptFunctionLike(FunctionLike):
    is_async: bool = False
    is_generator: bool = False
    is_exported: bool = False
    is_default_export: bool = False


class JavaScriptVariable(PythonVariable):
    declaration_kind: str | None = None
    is_exported: bool = False
    is_default_export: bool = False


class JavaScriptClass(Class):
    declaration_kind: str = "class"
    methods: list[JavaScriptFunctionLike] = Field(default_factory=list)
    inner_classes: list["JavaScriptClass"] = Field(default_factory=list)
    class_variables: list[JavaScriptVariable] = Field(default_factory=list)
    extends: str | None = None
    implements: list[str] = Field(default_factory=list)
    is_exported: bool = False
    is_default_export: bool = False


class ParsedJavaScriptSourceFile(SourceFile):
    classes: list[JavaScriptClass] = Field(default_factory=list)
    functions: list[JavaScriptFunctionLike] = Field(default_factory=list)
    variables: list[JavaScriptVariable] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedTypeScriptSourceFile(ParsedJavaScriptSourceFile):
    declaration_file: bool = False


Class.model_rebuild()
PythonClass.model_rebuild()
TypeDeclaration.model_rebuild()
ConditionalBlock.model_rebuild()
SourceFile.model_rebuild()
ParsedPythonSourceFile.model_rebuild()
ParsedJavaSourceFile.model_rebuild()
JavaScriptClass.model_rebuild()
ParsedJavaScriptSourceFile.model_rebuild()
ParsedTypeScriptSourceFile.model_rebuild()
