from __future__ import annotations
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from ..context import Context

T_In = TypeVar("T_In")
T_Out = TypeVar("T_Out")

@runtime_checkable
class Resolver(Protocol[T_In, T_Out]):
    def resolve(self, data_in: T_In, context: Context) -> T_Out:
        ...

__all__ = ["Resolver"]