from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from ..context import Context

from .parser.models import Node, SourceFile

T_In = TypeVar("T_In", bound=SourceFile)
T_Out = TypeVar("T_Out", bound=Node)


@runtime_checkable
class Linker(Protocol[T_In, T_Out]):
    def link_files(self, nodes: list[T_In], context: Context) -> list[T_Out]: ...
