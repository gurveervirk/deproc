import fnmatch
from deproc.core.interfaces import Linker
from deproc.core.context import Context
from pathlib import Path
from ..parser.models import PythonModule
from .models import (
    Node,
    PythonNamespacePackage,
    PythonPackage,
)

class PythonLinker(Linker[list[PythonModule], list[Node]]):
    def _check_skip_patterns(self, path: str, skip_patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in skip_patterns)

    def link_files(self, nodes: list[PythonModule], context: Context) -> list[Node]:
        base_path = Path(context.base_path)

        path_to_module: dict[str, PythonModule] = {}
        has_init: dict[str, PythonModule] = {}

        for node in nodes:
            relative_path = node.path
            dir_path = str(Path(relative_path).parent)

            if node.path.endswith("__init__.py"):
                has_init[dir_path] = node
                continue

            path_to_module[relative_path] = node

        skip_patterns = context.skip_paths
        top_level: list[Node] = []
        for sub_path in base_path.iterdir():
            if sub_path.name == "__pycache__":
                continue
            if self._check_skip_patterns(sub_path.name, skip_patterns):
                continue
            if not self.validate_path(str(sub_path)):
                continue
            sub_node = self.traverse_path(base_path, sub_path, path_to_module, has_init, context)
            if sub_node:
                sub_node.parent_id = None
                top_level.append(sub_node)

        return top_level

    def validate_path(self, path: str) -> bool:
        return path.endswith(".py") or path.endswith(".pyi") or path.endswith("__init__.py") or Path(path).is_dir()

    def traverse_path(
        self, 
        base_path: Path, 
        current_path: Path, 
        path_to_module: dict[str, PythonModule], 
        has_init: dict[str, PythonModule],
        context: Context
    ) -> Node | None:
        if not self.validate_path(str(current_path)):
            return None
        
        relative_path = str(current_path.relative_to(base_path)).replace("\\", "/")

        if relative_path.endswith(".py") or relative_path.endswith(".pyi"):
            return path_to_module.get(relative_path)

        package = None
        fqn = relative_path.replace("/", ".")

        if relative_path in has_init:
            package = PythonPackage(
                submodule_ids=[],
                **vars(has_init[relative_path])
            )
        else:
            package = PythonNamespacePackage(
                path=relative_path,
                fqn=fqn,
                submodule_ids=[],
            )

        for sub_path in current_path.iterdir():
            if sub_path.name == "__pycache__":
                continue
            if self._check_skip_patterns(sub_path.name, context.skip_paths):
                continue
            sub_node = self.traverse_path(base_path, sub_path, path_to_module, has_init, context)
            if sub_node:
                sub_node.parent_id = package.id
                package.submodule_ids.append(sub_node.id)

        context.entity_registry.add(package)
        return package
