from typing import Protocol, TypeVar, runtime_checkable
from .parser.models import SourceFile, Node
from ..context import Context

T_In = TypeVar("T_In", bound=list[SourceFile])
T_Out = TypeVar("T_Out", bound=list[Node])

@runtime_checkable
class Linker(Protocol[T_In, T_Out]):
    def link_files(self, nodes: T_In, context: Context) -> T_Out:
        ...