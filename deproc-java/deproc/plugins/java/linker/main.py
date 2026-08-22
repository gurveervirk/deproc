import os

from deproc.core.context import Context
from deproc.core.interfaces import Linker

from ..parser.models import JavaCompilationUnit, JavaModule
from .models import JavaPackage


class JavaLinker(Linker[JavaCompilationUnit | JavaModule, JavaPackage | JavaModule]):
    def link_files(
        self, nodes: list[JavaCompilationUnit | JavaModule], context: Context
    ) -> list[JavaPackage | JavaModule]:
        package_map: dict[str, JavaPackage] = {}
        modules: list[JavaModule] = []
        compilation_units: list[JavaCompilationUnit] = []

        for node in nodes:
            if isinstance(node, JavaModule):
                modules.append(node)
            else:
                compilation_units.append(node)

        def get_or_create_package(fqn: str) -> JavaPackage:
            if fqn not in package_map:
                package_map[fqn] = JavaPackage(
                    path=fqn.replace(".", "/"),
                    fqn=fqn,
                )
            return package_map[fqn]

        for node in compilation_units:
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

        for module in modules:
            self._assign_compilation_units(module, compilation_units, package_map)

        for pkg in package_map.values():
            context.entity_registry.add(pkg)

        for module in modules:
            context.entity_registry.add(module)

        top_level = [pkg for pkg in package_map.values() if pkg.parent_id is None]
        return modules + top_level

    def _assign_compilation_units(
        self,
        module: JavaModule,
        compilation_units: list[JavaCompilationUnit],
        package_map: dict[str, JavaPackage],
    ) -> None:
        module_root = os.path.dirname(module.path)
        prefix = f"{module_root}/" if module_root else ""
        package_ids: set[str] = set()

        for node in compilation_units:
            if module_root and not node.path.startswith(prefix):
                continue
            if node.id not in module.compilation_unit_ids:
                module.compilation_unit_ids.append(node.id)
            if node.package_fqn and node.package_fqn in package_map:
                package_ids.add(package_map[node.package_fqn].id)

        module.package_ids = sorted(package_ids)
