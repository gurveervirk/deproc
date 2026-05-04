from pathlib import Path

def find_source_files(root_path: str, file_extensions: list[str]) -> list[str]:
    root = Path(root_path)
    extension_set = set(file_extensions)
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