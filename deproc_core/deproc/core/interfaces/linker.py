from typing import Protocol, TypeVar, runtime_checkable
from .parser.models import SourceFile

T_Context = TypeVar("T_Context", bound=list[SourceFile])
T_Out = TypeVar("T_Out", covariant=True)

@runtime_checkable
class Linker(Protocol[T_Context, T_Out]):
    def link_files(self, extraction_context: T_Context) -> T_Out:
        ...