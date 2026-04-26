from typing import Any, Dict, Protocol, runtime_checkable

@runtime_checkable
class SourceParser(Protocol):
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        ...
