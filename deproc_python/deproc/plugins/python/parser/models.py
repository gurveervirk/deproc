from deproc.core.interfaces.parser.models import (
    Annotation,
    ComplexBinding,
    ControlFlowBlock,
    ControlFlowGroup,
    FunctionLike,
    ImportStatement,
    Signature,
    SimpleBinding,
    SourceFile,
    SourceRange,
    TypeDefinition,
    VariableDeclaration,
    generate_id
)
from dataclasses import dataclass, field

@dataclass(kw_only=True)
class PythonFunctionLike(FunctionLike):
    annotations: list[Annotation]
    visibility: str

@dataclass(kw_only=True)
class PythonConstant(VariableDeclaration):
    type: str = field(default="CONSTANT")

@dataclass(kw_only=True)
class PythonTypeAlias(VariableDeclaration):
    type: str = field(default="TYPE_ALIAS")

@dataclass(kw_only=True)
class PythonClass(TypeDefinition):
    type: str = field(default="CLASS")

@dataclass(kw_only=True)
class PythonImportAlias:
    name: str
    alias: str | None

@dataclass(kw_only=True)
class PythonImportStatement(ImportStatement):
    path: str
    names: list[PythonImportAlias]
    wildcard: bool = False

@dataclass(kw_only=True)
class PythonSourceFile(SourceFile):
    all_exports: list[str] | None = None

__all__ = [
    "ComplexBinding",
    "ControlFlowBlock",
    "ControlFlowGroup",
    "ImportStatement",
    "SimpleBinding",
    "Signature",
    "SourceFile",
    "SourceRange",
    "PythonClass",
    "PythonConstant",
    "PythonFunctionLike",
    "PythonSourceFile",
    "PythonTypeAlias",
    "VariableDeclaration",
    "generate_id"
]