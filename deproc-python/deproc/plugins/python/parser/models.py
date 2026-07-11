from deproc.core.interfaces.parser.models import (
    Annotation,
    ComplexBinding,
    ControlFlowBlock,
    ControlFlowGroup,
    Entity,
    FunctionLike,
    ImportStatement,
    Signature,
    SimpleBinding,
    SourceFile,
    SourceRange,
    SymbolID,
    TypeDefinition,
    VariableDeclaration,
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
class PythonImportAlias(Entity):
    name: str
    alias: str | None
    source_range: SourceRange
    fqn: str | None = None

@dataclass(kw_only=True)
class PythonImportStatement(ImportStatement):
    path: str
    name_ids: list[SymbolID] = field(default_factory=list)
    wildcard: bool = False

@dataclass(kw_only=True)
class PythonModule(SourceFile):
    fqn: str
    all_exports: list[str] | None = None

__all__ = [
    "ComplexBinding",
    "ControlFlowBlock",
    "ControlFlowGroup",
    "ImportStatement",
    "PythonClass",
    "PythonConstant",
    "PythonFunctionLike",
    "PythonModule",
    "PythonTypeAlias",
    "SimpleBinding",
    "Signature",
    "SourceFile",
    "SourceRange",
    "SymbolID",
    "VariableDeclaration",
]