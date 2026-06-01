from deproc.core.interfaces import Linker
from deproc.core.context import Context
from pathlib import Path
from uuid import uuid4
from .models import (
    Node,
    PythonModule,
    PythonNamespacePackage,
    PythonPackage,
    PythonSourceFile,
)

class PythonLinker(Linker[list[PythonSourceFile], Node]):
    def link_files(self, nodes: list[PythonSourceFile], context: Context) -> Node:
        base_path = Path(context.base_path)

        # Map relative path to modules
        path_to_module: dict[str, PythonModule] = {}

        # Check if dir has an __init__.py file
        has_init: dict[str, PythonSourceFile] = {}

        for node in nodes:
            relative_path = node.path
            dir_path = str(Path(relative_path).parent)
            
            if dir_path == ".":
                # handle special case where parent of root relative path is "."
                pass

            if node.path.endswith("__init__.py"):
                has_init[dir_path] = node
                continue

            node_fqn = None
            if node.path.endswith(".py"):
                node_fqn = relative_path[:-3].replace("/", ".")
            elif node.path.endswith(".pyi"):
                node_fqn = relative_path[:-4].replace("/", ".")
            
            if node_fqn is not None:
                mod = PythonModule(
                    fqn=node_fqn,
                    **vars(node)
                )
                path_to_module[relative_path] = mod
                context.entity_registry.add(mod)
        
        # Traverse the directory structure starting from the base path
        root_node = self.traverse_path(base_path, base_path, path_to_module, has_init, context)
        
        # Ensure root node is in the context
        if root_node and root_node.id not in context.entity_registry:
            context.entity_registry.add(root_node)
            
        return root_node

    def validate_path(self, path: str) -> bool:
        return path.endswith(".py") or path.endswith(".pyi") or path.endswith("__init__.py") or Path(path).is_dir()

    def traverse_path(
            self, 
            base_path: Path, 
            current_path: Path, 
            path_to_module: dict[str, PythonModule], 
            has_init: dict[str, PythonSourceFile],
            context: Context
        ) -> Node | None:
        if not self.validate_path(str(current_path)):
            return None
        
        relative_path = str(current_path.relative_to(base_path)).replace("\\", "/")

        if relative_path.endswith(".py") or relative_path.endswith(".pyi"):
            return path_to_module.get(relative_path)
        
        package = None

        fqn = relative_path.replace("/", ".") if relative_path != "." else ""
        if fqn == "":
            fqn = base_path.name

        if relative_path in has_init:
            package = PythonPackage(
                fqn=fqn,
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
                
            sub_node = self.traverse_path(base_path, sub_path, path_to_module, has_init, context)
            if sub_node:
                # Store parent ID
                sub_node.parent_id = package.id
                package.submodule_ids.append(sub_node.id)
                
        context.entity_registry.add(package)
        return package
