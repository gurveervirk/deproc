from typing import(
    ParamSpec,
    Protocol, 
    TypeVar, 
    runtime_checkable
)

TCache = TypeVar("TCache")
TReturn = TypeVar("TReturn")
PGet = ParamSpec("PGet")
PSet = ParamSpec("PSet")

@runtime_checkable
class SymbolCache(Protocol[TCache, TReturn, PGet, PSet]):
    language: str
    cache: TCache

    def get(self, *args: PGet.args, **kwargs: PGet.kwargs) -> TReturn:
        ...

    def set(self, *args: PSet.args, **kwargs: PSet.kwargs) -> None:
        ...