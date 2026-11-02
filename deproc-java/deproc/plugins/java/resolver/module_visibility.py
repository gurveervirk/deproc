from __future__ import annotations

from dataclasses import dataclass, field

from deproc.core.runtime.registries.entity import EntityRegistry

from ..parser.models import JavaModule

JAVA_BASE = "java.base"


@dataclass
class ModuleIndex:
    module_by_name: dict[str, JavaModule] = field(default_factory=dict)
    cu_to_module: dict[str, str] = field(default_factory=dict)
    package_to_modules: dict[str, set[str]] = field(default_factory=dict)

    @property
    def package_to_module(self) -> dict[str, str]:
        return {
            package: next(iter(modules))
            for package, modules in self.package_to_modules.items()
            if len(modules) == 1
        }


def build_module_index(registry: EntityRegistry) -> ModuleIndex:
    index = ModuleIndex()

    for entity in registry.values():
        if not isinstance(entity, JavaModule):
            continue
        index.module_by_name[entity.module_name] = entity
        for cu_id in entity.compilation_unit_ids:
            index.cu_to_module[cu_id] = entity.module_name
        for pkg_id in entity.package_ids:
            pkg = registry.get(pkg_id)
            pkg_fqn = getattr(pkg, "fqn", None)
            if pkg_fqn:
                index.package_to_modules.setdefault(pkg_fqn, set()).add(
                    entity.module_name
                )

    return index


def candidate_package(fqn: str, index: ModuleIndex) -> str | None:
    parts = fqn.split(".")
    for i in range(len(parts) - 1, 0, -1):
        pkg = ".".join(parts[:i])
        if pkg in index.package_to_modules:
            return pkg
    return None


def candidate_package_and_module(
    fqn: str, index: ModuleIndex
) -> tuple[str | None, str | None]:
    package = candidate_package(fqn, index)
    if package is None:
        return None, None
    modules = index.package_to_modules[package]
    if len(modules) == 1:
        return package, next(iter(modules))
    return package, None


def readable_modules(requester: str, index: ModuleIndex) -> set[str]:
    requester_module = index.module_by_name.get(requester)
    if requester_module is None:
        return set()

    readable: set[str] = {JAVA_BASE}
    readable.update(requester_module.requires)
    readable.update(requester_module.requires_static)
    readable.update(requester_module.requires_transitive)

    traversed: set[str] = set()

    def propagate(name: str) -> None:
        if name in traversed:
            return
        traversed.add(name)
        mod = index.module_by_name.get(name)
        if mod is None:
            return
        readable.update(mod.requires)
        readable.update(mod.requires_transitive)
        for r in mod.requires_transitive:
            propagate(r)

    for r in requester_module.requires_transitive:
        propagate(r)

    return readable


def is_exported_to(
    exports_module: str,
    package: str | None,
    requester: str,
    index: ModuleIndex,
) -> bool:
    mod = index.module_by_name.get(exports_module)
    if mod is None or package is None:
        return False
    if package in mod.exports:
        return True
    return requester in mod.qualified_exports.get(package, [])


def _module_can_see(
    requester_module: str,
    candidate_module: str,
    package: str | None,
    index: ModuleIndex,
) -> bool:
    if candidate_module == requester_module:
        return True
    if candidate_module not in readable_modules(requester_module, index):
        return False
    return is_exported_to(candidate_module, package, requester_module, index)


def is_visible(
    requester_module: str | None,
    candidate_fqn: str,
    index: ModuleIndex,
    candidate_module: str | None = None,
) -> bool:
    if requester_module is None:
        return True

    package = candidate_package(candidate_fqn, index)
    if candidate_module is not None:
        candidate_modules = {candidate_module}
        if package is None:
            package = candidate_fqn.rsplit(".", 1)[0] if "." in candidate_fqn else None
    elif package is not None:
        candidate_modules = index.package_to_modules[package]
    else:
        return True

    return any(
        _module_can_see(requester_module, module, package, index)
        for module in candidate_modules
    )
