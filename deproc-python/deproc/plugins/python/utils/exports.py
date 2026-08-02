from __future__ import annotations
from typing import TYPE_CHECKING
from collections import defaultdict
from ..parser.models import PythonModule

if TYPE_CHECKING:
    from deproc.core.runtime.registries.entity import EntityRegistry


def build_module_exports(registry: EntityRegistry) -> dict[str, set[str]]:
    exports: dict[str, set[str]] = defaultdict(set)
    for entity in registry.values():
        if isinstance(entity, PythonModule) and hasattr(entity, "all_exports") and entity.all_exports:
            for name in entity.all_exports:
                exports[entity.fqn].add(name)
    return dict(exports)
