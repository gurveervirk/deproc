from typing import(
    Any,
    Protocol, 
    TypeVar, 
    runtime_checkable
)

TCache = TypeVar("TCache")
TReturn = TypeVar("TReturn")

@runtime_checkable
class SymbolCache(Protocol[TCache, TReturn]):
    language: str
    cache: TCache

    def get(self, *args: Any, **kwargs: Any) -> TReturn:
        ...

    def set(self, *args: Any, **kwargs: Any) -> None:
        ...