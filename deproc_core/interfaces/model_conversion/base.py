from ..parser.models import SourceFile
from .models import ModelConversionResult
from typing import Protocol, TypeVar, runtime_checkable

T_SourceFile = TypeVar("T_SourceFile", bound=SourceFile)

@runtime_checkable
class ModelConverter(Protocol[T_SourceFile]):
    def convert_source_files(self, source_files: list[T_SourceFile]) -> ModelConversionResult:
        ...