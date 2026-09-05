import logging

from deproc.core.context import Context
from deproc.core.interfaces.parser.models import Entity, TypeDefinition
from deproc.core.interfaces.resolver import ResolutionResult, ResolutionStatus, Resolver

from ..parser.models import (
    JavaCompilationUnit,
    JavaImport,
    SymbolID,
)
from ..utils.imports import resolve_java_import
from .models import (
    JavaResolverResult,
)
from .module_visibility import build_module_index, is_visible

logger = logging.getLogger(__name__)


class JavaResolver(Resolver[JavaResolverResult]):
    def _get_compilation_units(
        self,
        compilation_unit_fqn: str,
        context: Context,
    ) -> list[JavaCompilationUnit]:
        units = []
        for entity_id in sorted(
            context.entity_registry.get_ids_by_fqn(compilation_unit_fqn)
        ):
            entity = context.entity_registry.get(entity_id)
            if isinstance(entity, JavaCompilationUnit):
                units.append(entity)
        return units

    def _get_compilation_unit(
        self,
        compilation_unit_fqn: str,
        context: Context,
    ) -> JavaCompilationUnit | None:
        units = self._get_compilation_units(compilation_unit_fqn, context)
        return units[0] if len(units) == 1 else None

    def _lookup_fqn(self, fqn: str, context: Context) -> set[SymbolID]:
        return context.entity_registry.get_ids_by_fqn(fqn)

    def _get_compilation_unit_for_type(
        self,
        type_entity: TypeDefinition,
        context: Context,
    ) -> JavaCompilationUnit | None:
        current: Entity | None = type_entity
        seen: set[SymbolID] = set()
        while current is not None and current.id not in seen:
            seen.add(current.id)
            if isinstance(current, JavaCompilationUnit):
                return current
            parent_id = getattr(current, "parent_id", None)
            current = context.entity_registry.get(parent_id) if parent_id else None
        return None

    def _type_candidates(
        self,
        raw_name: str,
        owner: TypeDefinition,
        context: Context,
    ) -> set[SymbolID]:
        name = raw_name.strip()
        if not name:
            return set()

        compilation_unit = self._get_compilation_unit_for_type(owner, context)
        candidate_fqns: list[str] = [name]
        if compilation_unit is not None and compilation_unit.package_fqn:
            candidate_fqns.append(f"{compilation_unit.package_fqn}.{name}")

        if compilation_unit is not None:
            for import_id in compilation_unit.import_stmt_ids:
                import_entity = context.entity_registry.get(import_id)
                if not isinstance(import_entity, JavaImport):
                    continue
                if import_entity.import_kind == "single_type":
                    if import_entity.imported_name == name:
                        candidate_fqns.append(import_entity.import_path)
                elif import_entity.import_kind == "on_demand":
                    candidate_fqns.append(f"{import_entity.import_path[:-2]}.{name}")

        candidate_fqns.append(f"java.lang.{name}")
        candidates: set[SymbolID] = set()
        for fqn in dict.fromkeys(candidate_fqns):
            for entity_id in context.entity_registry.get_ids_by_fqn(fqn):
                entity = context.entity_registry.get(entity_id)
                if isinstance(entity, TypeDefinition):
                    candidates.add(entity_id)
        return candidates

    def resolve_type_reference(
        self,
        raw_name: str,
        owner: TypeDefinition,
        context: Context,
    ) -> ResolutionResult[SymbolID]:
        candidates = self._type_candidates(raw_name, owner, context)
        if not candidates:
            return ResolutionResult(
                status=ResolutionStatus.UNRESOLVED,
                reason=f"No type found for '{raw_name}'",
            )

        module_index = build_module_index(context.entity_registry)
        requester_module = module_index.cu_to_module.get(
            getattr(self._get_compilation_unit_for_type(owner, context), "id", "")
        )
        visible: list[SymbolID] = []
        inaccessible: list[SymbolID] = []
        for entity_id in sorted(candidates):
            entity = context.entity_registry.get(entity_id)
            fqn = getattr(entity, "fqn", None)
            if fqn and is_visible(requester_module, fqn, module_index):
                visible.append(entity_id)
            else:
                inaccessible.append(entity_id)

        if not visible:
            return ResolutionResult(
                status=ResolutionStatus.INACCESSIBLE,
                candidates=tuple(inaccessible),
                reason=f"Types matching '{raw_name}' are inaccessible",
            )
        if len(visible) > 1:
            return ResolutionResult(
                status=ResolutionStatus.AMBIGUOUS,
                candidates=tuple(visible),
                reason=f"Multiple types found for '{raw_name}'",
            )
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            value=visible[0],
            candidates=(visible[0],),
        )

    def resolve(
        self,
        compilation_unit_fqn: str,
        symbol_name: str,
        context: Context,
    ) -> JavaResolverResult:
        symbol_cache = context.get_symbol_cache("java")
        if symbol_cache is not None:
            cached = symbol_cache.get(compilation_unit_fqn, symbol_name)
            if cached is not None:
                cached_resolved = set(cached[0])
                return JavaResolverResult(
                    resolved_ids=cached_resolved,
                    unresolved_ids=set(cached[1]),
                    inaccessible_ids=set(cached[2]),
                    ambiguous_ids=(
                        cached_resolved if len(cached_resolved) > 1 else set()
                    ),
                )

        resolved_ids: set[SymbolID] = set()
        unresolved_ids: set[SymbolID] = set()
        inaccessible_ids: set[SymbolID] = set()

        compilation_units = self._get_compilation_units(compilation_unit_fqn, context)
        if len(compilation_units) != 1:
            ambiguous_ids = {unit.id for unit in compilation_units}
            logger.warning(
                f"Compilation unit not found for FQN: {compilation_unit_fqn}"
            )
            result = JavaResolverResult(
                resolved_ids=set(),
                unresolved_ids=set(),
                inaccessible_ids=set(),
                ambiguous_ids=ambiguous_ids,
            )
            if symbol_cache is not None:
                symbol_cache.set(
                    compilation_unit_fqn,
                    symbol_name,
                    result.resolved_ids,
                    result.unresolved_ids,
                    result.inaccessible_ids,
                )
            return result
        compilation_unit = compilation_units[0]

        package_fqn = compilation_unit.package_fqn

        if package_fqn:
            resolved_ids.update(
                self._lookup_fqn(f"{package_fqn}.{symbol_name}", context)
            )
        else:
            resolved_ids.update(self._lookup_fqn(symbol_name, context))

        resolved_ids.update(self._lookup_fqn(f"java.lang.{symbol_name}", context))

        for import_id in compilation_unit.import_stmt_ids:
            import_entity = context.entity_registry.get(import_id)
            if not isinstance(import_entity, JavaImport):
                continue

            if (
                import_entity.import_kind in ("single_type", "single_static")
                and import_entity.imported_name != symbol_name
            ):
                continue

            base_fqn = resolve_java_import(
                import_entity.import_path,
                import_entity.import_kind,
            )

            if import_entity.import_kind == "single_type":
                candidate_fqn = base_fqn
            else:
                candidate_fqn = f"{base_fqn}.{symbol_name}"

            found = self._lookup_fqn(candidate_fqn, context)
            if found:
                resolved_ids.update(found)
            else:
                unresolved_ids.add(import_entity.id)

        module_index = build_module_index(context.entity_registry)
        if module_index.module_by_name:
            requesting_module = module_index.cu_to_module.get(compilation_unit.id)
            visible_ids: set[SymbolID] = set()
            for resolved_id in resolved_ids:
                entity = context.entity_registry.get(resolved_id)
                fqn = getattr(entity, "fqn", None) or getattr(
                    getattr(entity, "variable_binding", None), "fqn", None
                )
                if not fqn or is_visible(requesting_module, fqn, module_index):
                    visible_ids.add(resolved_id)
                else:
                    inaccessible_ids.add(resolved_id)
            resolved_ids = visible_ids

        result = JavaResolverResult(
            resolved_ids=resolved_ids,
            unresolved_ids=unresolved_ids,
            inaccessible_ids=inaccessible_ids,
            ambiguous_ids=resolved_ids if len(resolved_ids) > 1 else set(),
        )

        if symbol_cache is not None:
            symbol_cache.set(
                compilation_unit_fqn,
                symbol_name,
                result.resolved_ids,
                result.unresolved_ids,
                result.inaccessible_ids,
            )
        return result
