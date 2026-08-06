from deproc.core.interfaces import Linker
from deproc.core.context import Context
from ..parser.models import JavaCompilationUnit
from .models import (
    JavaPackage,
    Node,
)

class JavaLinker(Linker[list[JavaCompilationUnit], list[Node]]):
    def link_files(self, nodes: list[JavaCompilationUnit], context: Context) -> list[Node]:
        package_map: dict[str, JavaPackage] = {}

        def get_or_create_package(fqn: str) -> JavaPackage:
            if fqn not in package_map:
                package_map[fqn] = JavaPackage(
                    path=fqn.replace(".", "/"),
                    fqn=fqn,
                )
            return package_map[fqn]

        for node in nodes:
            package_fqn = node.package_fqn
            if not package_fqn:
                continue
            pkg = get_or_create_package(package_fqn)
            if node.id not in pkg.compilation_unit_ids:
                pkg.compilation_unit_ids.append(node.id)

        for pkg_fqn in list(package_map.keys()):
            parts = pkg_fqn.split(".")
            for i in range(1, len(parts)):
                get_or_create_package(".".join(parts[:i]))

        for pkg_fqn, pkg in package_map.items():
            parts = pkg_fqn.split(".")
            if len(parts) > 1:
                parent_fqn = ".".join(parts[:-1])
                parent = package_map.get(parent_fqn)
                if parent is not None and parent.id != pkg.id:
                    pkg.parent_id = parent.id
                    if pkg.id not in parent.subpackage_ids:
                        parent.subpackage_ids.append(pkg.id)

        for pkg in package_map.values():
            context.entity_registry.add(pkg)

        top_level = [pkg for pkg in package_map.values() if pkg.parent_id is None]
        return top_level
