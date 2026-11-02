import os

from deproc.core.context import Context
from deproc.core.interfaces import Linker
from deproc.core.interfaces.parser.models import SemanticContainer

from ..parser.models import JavaCompilationUnit, JavaModule, JavaPackageInfo
from .models import JavaPackage


class JavaLinker(
    Linker[
        JavaCompilationUnit | JavaModule | JavaPackageInfo,
        SemanticContainer | JavaModule,
    ]
):
    def link_files(
        self,
        nodes: list[JavaCompilationUnit | JavaModule | JavaPackageInfo],
        context: Context,
    ) -> list[SemanticContainer | JavaModule]:
        package_map: dict[tuple[str | None, str], JavaPackage] = {}
        modules: list[JavaModule] = []
        compilation_units: list[JavaCompilationUnit | JavaPackageInfo] = []
        package_infos: list[JavaPackageInfo] = []

        for node in nodes:
            if isinstance(node, JavaModule):
                modules.append(node)
            elif isinstance(node, JavaPackageInfo):
                compilation_units.append(node)
                package_infos.append(node)
            else:
                compilation_units.append(node)

        owners: dict[str, JavaModule | None] = {
            node.id: self._owning_module(node, modules) for node in compilation_units
        }

        def module_name_of(node: JavaCompilationUnit | JavaPackageInfo) -> str | None:
            owner = owners.get(node.id)
            return owner.module_name if owner is not None else None

        def get_or_create_package(module_name: str | None, fqn: str) -> JavaPackage:
            key = (module_name, fqn)
            if key not in package_map:
                package_map[key] = JavaPackage(
                    path=fqn.replace(".", "/"),
                    fqn=fqn,
                    module_name=module_name,
                )
            return package_map[key]

        for node in compilation_units:
            package_fqn = node.package_fqn
            if not package_fqn:
                continue
            pkg = get_or_create_package(module_name_of(node), package_fqn)
            if node.id not in pkg.compilation_unit_ids:
                pkg.compilation_unit_ids.append(node.id)

        for module_name, pkg_fqn in list(package_map.keys()):
            parts = pkg_fqn.split(".")
            for i in range(1, len(parts)):
                get_or_create_package(module_name, ".".join(parts[:i]))

        for (module_name, pkg_fqn), pkg in package_map.items():
            parts = pkg_fqn.split(".")
            if len(parts) > 1:
                parent_fqn = ".".join(parts[:-1])
                parent = package_map.get((module_name, parent_fqn))
                if parent is not None and parent.id != pkg.id:
                    pkg.parent_id = parent.id
                    if pkg.id not in parent.subpackage_ids:
                        parent.subpackage_ids.append(pkg.id)

        for module in modules:
            self._assign_compilation_units(
                module, compilation_units, owners, package_map
            )

        for package_info in package_infos:
            pkg = package_map.get(
                (module_name_of(package_info), package_info.package_fqn or "")
            )
            if pkg is not None:
                pkg.package_info_id = package_info.id
                pkg.package_info_ids = sorted(
                    set(pkg.package_info_ids) | {package_info.id}
                )

        for key, pkg in package_map.items():
            pkg.subpackage_ids = sorted(set(pkg.subpackage_ids))
            pkg.compilation_unit_ids = sorted(set(pkg.compilation_unit_ids))
            pkg.package_info_id = (
                min(pkg.package_info_ids) if pkg.package_info_ids else None
            )
            package_map[key] = context.entity_registry.merge_semantic_container(pkg)

        for module in modules:
            context.entity_registry.add(module)

        top_level_packages = sorted(
            (pkg for pkg in package_map.values() if pkg.parent_id is None),
            key=lambda pkg: (pkg.fqn, pkg.module_name or ""),
        )
        top_level: list[SemanticContainer | JavaModule] = list(top_level_packages)
        modules.sort(
            key=lambda module: (module.module_name, module.source_root_id or "")
        )
        return modules + top_level

    @staticmethod
    def _owning_module(
        node: JavaCompilationUnit | JavaPackageInfo, modules: list[JavaModule]
    ) -> JavaModule | None:
        best: JavaModule | None = None
        best_root = -1
        for module in modules:
            module_root = os.path.dirname(module.path)
            if module_root and not node.path.startswith(f"{module_root}/"):
                continue
            if len(module_root) > best_root:
                best = module
                best_root = len(module_root)
        return best

    def _assign_compilation_units(
        self,
        module: JavaModule,
        compilation_units: list[JavaCompilationUnit | JavaPackageInfo],
        owners: dict[str, JavaModule | None],
        package_map: dict[tuple[str | None, str], JavaPackage],
    ) -> None:
        package_ids: set[str] = set()

        for node in compilation_units:
            if owners.get(node.id) is not module:
                continue
            if node.id not in module.compilation_unit_ids:
                module.compilation_unit_ids.append(node.id)
            package = package_map.get((module.module_name, node.package_fqn or ""))
            if package is not None:
                package_ids.add(package.id)

        module.package_ids = sorted(package_ids)
        module.compilation_unit_ids.sort()
