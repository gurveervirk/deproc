from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from deproc.core.interfaces.parser.models import SymbolID
from deproc.core.runtime import EntityRegistry

from ..linker.models import PythonNamespacePackage, PythonPackage
from ..parser.models import PythonModule

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShadowedNamespacePortion:
    fqn: str
    path: str
    registry_index: int
    detached_ids: tuple[SymbolID, ...]


@dataclass(frozen=True)
class RegularPackageConflict:
    fqn: str
    source_root_ids: tuple[str | None, ...]


def _shadows(regular_fqns: set[str], fqn: str) -> bool:
    return any(
        fqn == regular or fqn.startswith(f"{regular}.") for regular in regular_fqns
    )


def _root_label(root_id: str | None) -> str:
    return root_id if root_id is not None else "<no root id>"


def _log_shadowed(fqn: str, detached: int) -> None:
    logger.warning(
        "namespace portion '%s' is shadowed by a regular package of the "
        "same name in another root; its %d module(s) stay indexed "
        "without a parent package",
        fqn,
        detached,
    )


def find_regular_package_conflicts(
    registries: Sequence[EntityRegistry],
) -> list[RegularPackageConflict]:
    by_fqn: dict[str, dict[SymbolID, PythonPackage]] = {}
    for registry in registries:
        for entity in registry.values():
            if isinstance(entity, PythonPackage):
                by_fqn.setdefault(entity.fqn, {})[entity.id] = entity
    return [
        RegularPackageConflict(
            fqn=fqn,
            source_root_ids=tuple(
                sorted(
                    (package.source_root_id for package in packages.values()),
                    key=lambda root_id: root_id or "",
                )
            ),
        )
        for fqn, packages in sorted(by_fqn.items())
        if len(packages) > 1
    ]


def _log_conflicts(conflicts: Sequence[RegularPackageConflict]) -> None:
    for conflict in conflicts:
        logger.warning(
            "regular package '%s' is defined in more than one root (%s); Python "
            "imports only the first one on its path, and all of them stay indexed",
            conflict.fqn,
            ", ".join(_root_label(root_id) for root_id in conflict.source_root_ids),
        )


def apply_regular_package_precedence(
    registries: Sequence[EntityRegistry],
) -> list[ShadowedNamespacePortion]:
    """Apply Python's rule that a regular package wins over a namespace portion.

    ``registries`` are the per-root link results, before they are merged. A
    namespace portion in one registry is shadowed when a different registry
    holds a regular package (one with ``__init__.py``) of the same name, or of
    an ancestor name. Python then never imports that portion, so its container
    is removed and the modules it held stay in the registry without a parent.
    A warning is logged for each regular package name that more than one
    registry defines; all of them are kept.
    """
    _log_conflicts(find_regular_package_conflicts(registries))
    regular_by_registry = [
        {
            entity.fqn
            for entity in registry.values()
            if isinstance(entity, PythonPackage)
        }
        for registry in registries
    ]
    shadowed: list[ShadowedNamespacePortion] = []
    for index, registry in enumerate(registries):
        foreign_regular = {
            fqn
            for other, fqns in enumerate(regular_by_registry)
            if other != index
            for fqn in fqns
        }
        if not foreign_regular:
            continue
        candidates = sorted(
            (
                entity
                for entity in registry.values()
                if isinstance(entity, PythonNamespacePackage)
                and _shadows(foreign_regular, entity.fqn)
            ),
            key=lambda entity: (entity.fqn, entity.path),
        )
        for container in candidates:
            if container.id not in registry:
                continue
            detached = _drop_portion(registry, container)
            portion = ShadowedNamespacePortion(
                fqn=container.fqn,
                path=container.path,
                registry_index=index,
                detached_ids=tuple(detached),
            )
            shadowed.append(portion)
            _log_shadowed(container.fqn, len(detached))
    return shadowed


def apply_regular_package_precedence_to_registry(
    registry: EntityRegistry,
) -> list[ShadowedNamespacePortion]:
    regular: dict[str, list[PythonPackage]] = {}
    for entity in registry.values():
        if isinstance(entity, PythonPackage):
            regular.setdefault(entity.fqn, []).append(entity)
    _log_conflicts(find_regular_package_conflicts([registry]))
    if not regular:
        return []

    containers = sorted(
        (
            entity
            for entity in registry.values()
            if isinstance(entity, PythonNamespacePackage)
            and _shadows(set(regular), entity.fqn)
        ),
        key=lambda entity: (-entity.fqn.count("."), entity.fqn, entity.path),
    )
    shadowed: list[ShadowedNamespacePortion] = []
    for container in containers:
        if container.id not in registry:
            continue
        exact = container.fqn in regular
        regular_roots = {
            package.source_root_id
            for fqn, packages in regular.items()
            if _shadows({fqn}, container.fqn)
            for package in packages
        }
        owner = (
            min(
                regular[container.fqn],
                key=lambda package: (package.source_root_id or "", package.path),
            )
            if exact
            else None
        )
        kept: list[SymbolID] = []
        detached: list[SymbolID] = []
        for child_id in container.submodule_ids:
            child = registry.get(child_id)
            if child is None:
                continue
            if isinstance(child, PythonNamespacePackage):
                if owner is not None:
                    child.parent_id = owner.id
                    if child.id not in owner.submodule_ids:
                        owner.submodule_ids.append(child.id)
                else:
                    kept.append(child_id)
                continue
            if (
                owner is None
                and isinstance(child, PythonModule)
                and child.source_root_id in regular_roots
            ):
                kept.append(child_id)
                continue
            child.parent_id = None
            detached.append(child.id)
        removed = owner is not None or (bool(detached) and not kept)
        if removed:
            parent = registry.get(container.parent_id) if container.parent_id else None
            if isinstance(parent, (PythonNamespacePackage, PythonPackage)):
                parent.submodule_ids = [
                    entity_id
                    for entity_id in parent.submodule_ids
                    if entity_id != container.id
                ]
            registry.remove(container.id)
        else:
            container.submodule_ids = kept
        if removed or detached:
            shadowed.append(
                ShadowedNamespacePortion(
                    fqn=container.fqn,
                    path=container.path,
                    registry_index=0,
                    detached_ids=tuple(sorted(detached)),
                )
            )
            _log_shadowed(container.fqn, len(detached))
    shadowed.sort(key=lambda portion: (portion.fqn, portion.path))
    return shadowed


def _drop_portion(
    registry: EntityRegistry, container: PythonNamespacePackage
) -> list[SymbolID]:
    detached: list[SymbolID] = []
    pending = [container]
    while pending:
        current = pending.pop()
        parent = registry.get(current.parent_id) if current.parent_id else None
        if isinstance(parent, (PythonNamespacePackage, PythonPackage)):
            parent.submodule_ids = [
                entity_id
                for entity_id in parent.submodule_ids
                if entity_id != current.id
            ]
        registry.remove(current.id)
        for child_id in current.submodule_ids:
            child = registry.get(child_id)
            if child is None:
                continue
            if isinstance(child, PythonNamespacePackage):
                pending.append(child)
            else:
                child.parent_id = None
                detached.append(child.id)
    return sorted(detached)


__all__ = [
    "RegularPackageConflict",
    "ShadowedNamespacePortion",
    "apply_regular_package_precedence",
    "apply_regular_package_precedence_to_registry",
    "find_regular_package_conflicts",
]
