from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar, runtime_checkable

TOut = TypeVar("TOut")


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    INACCESSIBLE = "inaccessible"


@dataclass(frozen=True)
class ResolutionResult[TOut]:
    status: ResolutionStatus
    value: TOut | None = None
    candidates: tuple[TOut, ...] = ()
    reason: str | None = None


@runtime_checkable
class Resolver(Protocol[TOut]):
    def resolve(self, *args: Any, **kwargs: Any) -> TOut: ...


__all__ = ["ResolutionResult", "ResolutionStatus", "Resolver"]
