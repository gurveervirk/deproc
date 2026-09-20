import fnmatch
import os
from pathlib import Path

from .context import Context
from .scope import DiscoveredFile, RootDescriptor


def _match_any(name: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def _root_descriptors(context: Context) -> tuple[RootDescriptor, ...]:
    if context.scope.roots:
        return context.scope.roots
    if context.base_path:
        return (RootDescriptor(context.base_path),)
    return ()


_ROOT_KIND_PRECEDENCE = {
    "project": 0,
    "source": 1,
    "generated": 2,
    "declaration": 3,
    "dependency": 4,
}


def _root_preference(root: RootDescriptor) -> tuple[int, int, int, str]:
    specificity = len(Path(root.path).parts)
    kind_precedence = _ROOT_KIND_PRECEDENCE.get(root.kind, 100)
    provenance_precedence = 0 if root.provenance == "explicit" else 1
    return (-specificity, kind_precedence, provenance_precedence, root.root_id or "")


def discover_source_files(context: Context) -> list[DiscoveredFile]:
    extension_set = set(context.selected_file_extensions)
    skip_paths = set(context.skip_paths) | set(context.scope.exclusions)
    if not extension_set:
        return []

    matches: dict[str, DiscoveredFile] = {}
    for root in sorted(
        _root_descriptors(context),
        key=lambda item: (item.path, item.kind, item.provenance),
    ):
        for dirpath, dirnames, filenames in os.walk(root.path):
            dirnames[:] = sorted(d for d in dirnames if not _match_any(d, skip_paths))
            for filename in sorted(filenames):
                if _match_any(filename, skip_paths):
                    continue
                if not any(filename.lower().endswith(ext) for ext in extension_set):
                    continue
                path = os.path.abspath(os.path.join(dirpath, filename))
                candidate = DiscoveredFile(path=path, root=root)
                current = matches.get(path)
                if current is None or _root_preference(
                    candidate.root
                ) < _root_preference(current.root):
                    matches[path] = candidate

    return [matches[path] for path in sorted(matches)]


def find_source_files(context: Context) -> list[str]:
    return [item.path for item in discover_source_files(context)]


find_source_files_with_provenance = discover_source_files
