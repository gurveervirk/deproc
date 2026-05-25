from .context import Context
from pathlib import Path

def find_source_files(context: Context) -> list[str]:
    root = Path(context.base_path)
    extension_set = set(context.selected_file_extensions)
    if not extension_set:
        return []

    matches: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in extension_set:
            matches.append(str(path))

    matches.sort()
    return matches