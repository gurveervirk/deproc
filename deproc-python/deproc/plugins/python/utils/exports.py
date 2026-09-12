from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from ..parser.models import PythonModule
from .imports import resolve_relative_import_path

if TYPE_CHECKING:
    from deproc.core.runtime.registries.entity import EntityRegistry


def _entity_name(entity) -> str | None:
    name = getattr(entity, "name", None)
    if name:
        return name
    binding = getattr(entity, "variable_binding", None)
    return getattr(binding, "name", None)


def _module_target(import_statement, module: PythonModule, registry) -> str | None:
    path = getattr(import_statement, "path", None)
    if not path:
        return None
    if not path.startswith("."):
        return path
    is_package = getattr(module, "path", "").endswith(("__init__.py", "__init__.pyi"))
    return resolve_relative_import_path(path, module.fqn, is_package)


def _module_groups(registry: EntityRegistry) -> dict[str, list[PythonModule]]:
    groups: dict[str, list[PythonModule]] = defaultdict(list)
    for entity in registry.values():
        if isinstance(entity, PythonModule):
            groups[entity.fqn].append(entity)
    return dict(groups)


def _direct_exports(module: PythonModule, registry) -> set[str]:
    names: set[str] = set()
    child_ids = [
        *getattr(module, "type_ids", []),
        *getattr(module, "function_ids", []),
        *getattr(module, "variable_ids", []),
    ]
    for child_id in child_ids:
        child = registry.get(child_id)
        name = _entity_name(child) if child else None
        if name and not name.startswith("_"):
            names.add(name)

    for import_id in getattr(module, "import_stmt_ids", []):
        import_statement = registry.get(import_id)
        if import_statement is None or getattr(import_statement, "wildcard", False):
            continue
        for alias_id in getattr(import_statement, "name_ids", []):
            alias = registry.get(alias_id)
            if alias is None:
                continue
            name = getattr(alias, "alias", None) or getattr(alias, "name", "")
            if getattr(import_statement, "type", None) == "generic_import":
                name = name.split(".", 1)[0]
            if name and not name.startswith("_"):
                names.add(name)
    return names


def _compute_exports(
    registry: EntityRegistry,
) -> tuple[dict[str, set[str]], set[str]]:
    groups = _module_groups(registry)
    exports: dict[str, set[str]] = {}
    dynamic_modules: set[str] = set()
    state: dict[str, int] = {}

    def visit(module_fqn: str) -> set[str]:
        current_state = state.get(module_fqn, 0)
        if current_state == 1:
            dynamic_modules.add(module_fqn)
            return set()
        if current_state == 2:
            return exports.get(module_fqn, set())

        state[module_fqn] = 1
        modules = groups.get(module_fqn, [])
        names: set[str] = set()
        explicit = False
        explicit_names: set[str] = set()
        own_dynamic = False
        dependency_dynamic = False
        for module in modules:
            if getattr(module, "exports_dynamic", False):
                own_dynamic = True
            if module.all_exports is not None:
                explicit = True
                explicit_names.update(module.all_exports)
            else:
                names.update(_direct_exports(module, registry))

            for import_id in getattr(module, "import_stmt_ids", []):
                import_statement = registry.get(import_id)
                if import_statement is None or not getattr(
                    import_statement, "wildcard", False
                ):
                    continue
                target_fqn = _module_target(import_statement, module, registry)
                if not target_fqn:
                    dynamic = True
                    continue
                if target_fqn in groups:
                    names.update(visit(target_fqn))
                    dependency_dynamic = (
                        dependency_dynamic or target_fqn in dynamic_modules
                    )
                else:
                    dependency_dynamic = True

        if explicit:
            names = explicit_names
            dynamic = own_dynamic
        else:
            dynamic = own_dynamic or dependency_dynamic
        if not explicit and not modules:
            dynamic = True
        if dynamic:
            dynamic_modules.add(module_fqn)
        exports[module_fqn] = names
        state[module_fqn] = 2
        return names

    for module_fqn in groups:
        visit(module_fqn)
    return exports, dynamic_modules


def build_module_exports(registry: EntityRegistry) -> dict[str, set[str]]:
    exports, dynamic_modules = _compute_exports(registry)
    groups = _module_groups(registry)
    return {
        module_fqn: names
        for module_fqn, names in exports.items()
        if module_fqn not in dynamic_modules
        and (
            names
            or any(module.all_exports is not None for module in groups[module_fqn])
        )
    }


def get_dynamic_export_modules(registry: EntityRegistry) -> set[str]:
    return _compute_exports(registry)[1]
