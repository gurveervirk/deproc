from __future__ import annotations
from typing import (
    Any,
    Protocol,
    TypeVar,
    runtime_checkable
)

TOut = TypeVar("TOut")

@runtime_checkable
class Resolver(Protocol[TOut]):
    def resolve(self, *args: Any, **kwargs: Any) -> TOut:
        ...

__all__ = ["Resolver"]