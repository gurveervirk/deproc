from dataclasses import dataclass, field

from deproc.core.interfaces.parser.models import (
    Annotation,
    Entity,
    FunctionLike,
    Signature,
    SimpleBinding,
    SourceFile,
    SourceRange,
    SymbolID,
    TypeDefinition,
    VariableDeclaration,
)


@dataclass(kw_only=True)
class JavaCompilationUnit(SourceFile):
    fqn: str
    package_fqn: str | None = None


@dataclass(kw_only=True)
class JavaClass(TypeDefinition):
    type: str = field(default="CLASS")
    is_abstract: bool = False
    is_final: bool = False
    is_static: bool = False
    superclass: str | None = None
    implements: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class JavaInterface(TypeDefinition):
    type: str = field(default="INTERFACE")
    extends_interfaces: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class JavaEnum(TypeDefinition):
    type: str = field(default="ENUM")
    implements: list[str] = field(default_factory=list)
    enum_constant_ids: list[SymbolID] = field(default_factory=list)


@dataclass(kw_only=True)
class JavaRecord(TypeDefinition):
    type: str = field(default="RECORD")
    implements: list[str] = field(default_factory=list)
    record_component_ids: list[SymbolID] = field(default_factory=list)


@dataclass(kw_only=True)
class JavaAnnotationType(TypeDefinition):
    type: str = field(default="ANNOTATION_TYPE")


@dataclass(kw_only=True)
class JavaMethod(FunctionLike):
    type: str = field(default="METHOD")
    exceptions: list[str] = field(default_factory=list)
    is_abstract: bool = False
    is_final: bool = False
    is_static: bool = False
    is_default: bool = False
    is_synchronized: bool = False
    is_native: bool = False
    visibility: str = "package-private"
    annotations: list[Annotation] = field(default_factory=list)


@dataclass(kw_only=True)
class JavaField(VariableDeclaration):
    type: str = field(default="FIELD")
    is_static: bool = False
    is_final: bool = False
    is_transient: bool = False
    is_volatile: bool = False


@dataclass(kw_only=True)
class JavaEnumConstant(Entity):
    name: str
    fqn: str
    source_range: SourceRange
    arguments_range: SourceRange | None = None


@dataclass(kw_only=True)
class JavaRecordComponent(Entity):
    name: str
    fqn: str
    source_range: SourceRange
    type_annotation: SourceRange | None = None


@dataclass(kw_only=True)
class JavaImport(Entity):
    import_path: str = ""
    import_kind: str = ""
    imported_name: str | None = None
    source_range: SourceRange


__all__ = [
    "Annotation",
    "Entity",
    "FunctionLike",
    "JavaAnnotationType",
    "JavaClass",
    "JavaCompilationUnit",
    "JavaEnum",
    "JavaEnumConstant",
    "JavaField",
    "JavaImport",
    "JavaInterface",
    "JavaMethod",
    "JavaRecord",
    "JavaRecordComponent",
    "Signature",
    "SimpleBinding",
    "SourceFile",
    "SourceRange",
    "SymbolID",
    "TypeDefinition",
    "VariableDeclaration",
]
