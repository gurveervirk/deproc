import fnmatch
import os
from .context import Context

def _match_any(name: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)

def find_source_files(context: Context) -> list[str]:
    root = context.base_path
    extension_set = set(context.selected_file_extensions)
    skip_dirs = context.skip_paths
    if not extension_set:
        return []

    matches: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _match_any(d, skip_dirs)]
        for f in filenames:
            if any(f.lower().endswith(ext) for ext in extension_set):
                matches.append(os.path.join(dirpath, f))

    matches.sort()
    return matches