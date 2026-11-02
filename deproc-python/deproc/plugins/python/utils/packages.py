from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from deproc.core.interfaces.parser.models import SymbolID
from deproc.core.runtime import EntityRegistry

from ..linker.models import PythonNamespacePackage, PythonPackage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShadowedNamespacePortion:
    fqn: str
    path: str
    registry_index: int
    detached_ids: tuple[SymbolID, ...]


def _shadows(regular_fqns: set[str], fqn: str) -> bool:
    return any(
        fqn == regular or fqn.startswith(f"{regular}.") for regular in regular_fqns
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
    """
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
            logger.warning(
                "namespace portion '%s' is shadowed by a regular package of the "
                "same name in another root; its %d module(s) stay indexed "
                "without a parent package",
                container.fqn,
                len(detached),
            )
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


__all__ = ["ShadowedNamespacePortion", "apply_regular_package_precedence"]
