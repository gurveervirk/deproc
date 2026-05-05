from ..parser.models import SourceFile
from .models import ModelConversionResult
from typing import Protocol, runtime_checkable

@runtime_checkable
class ModelConverter(Protocol):
    def convert_source_files(self, source_files: list[SourceFile]) -> ModelConversionResult:
        ...