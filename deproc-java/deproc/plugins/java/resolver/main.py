import logging

from deproc.core.context import Context
from deproc.core.interfaces.parser.models import Entity, TypeDefinition
from deproc.core.interfaces.resolver import ResolutionResult, ResolutionStatus, Resolver

from ..parser.models import (
    JavaCompilationUnit,
    JavaImport,
    JavaInterface,
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

    def _lookup_type_fqn(self, fqn: str, context: Context) -> set[SymbolID]:
        return {
            entity_id
            for entity_id in self._lookup_fqn(fqn, context)
            if isinstance(context.entity_registry.get(entity_id), TypeDefinition)
        }

    def _get_compilation_unit_for_type(
        self,
        type_entity: Entity,
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

    def _current_compilation_unit_types(
        self,
        compilation_unit: JavaCompilationUnit | None,
        name: str,
        context: Context,
    ) -> set[SymbolID]:
        if compilation_unit is None:
            return set()

        type_ids = set(compilation_unit.type_ids)
        type_ids.update(
            entity.id
            for entity in context.entity_registry.values()
            if isinstance(entity, TypeDefinition)
            and getattr(entity, "parent_id", None) == compilation_unit.id
        )
        return {
            entity_id
            for entity_id in type_ids
            if (
                isinstance(
                    entity := context.entity_registry.get(entity_id), TypeDefinition
                )
                and entity.name == name
            )
        }

    def _enclosing_type_fqns(
        self,
        owner: Entity,
        context: Context,
    ) -> list[str]:
        fqns: list[str] = []
        current: Entity | None = owner
        seen: set[SymbolID] = set()
        while current is not None and current.id not in seen:
            seen.add(current.id)
            if not isinstance(current, TypeDefinition):
                break
            fqns.append(current.fqn)
            parent_id = getattr(current, "parent_id", None)
            current = context.entity_registry.get(parent_id) if parent_id else None
        return fqns

    def _type_candidate_tiers(
        self,
        raw_name: str,
        owner: Entity,
        context: Context,
    ) -> list[set[SymbolID]]:
        name = raw_name.strip()
        if not name:
            return []

        compilation_unit = self._get_compilation_unit_for_type(owner, context)

        if "." in name:
            components = name.split(".")
            leading_candidates = self._type_candidates(components[0], owner, context)
            if leading_candidates:
                member_candidates = self._lookup_member_type_components(
                    leading_candidates, components[1:], context
                )
                return [member_candidates]

            tiers: list[set[SymbolID]] = [self._lookup_type_fqn(name, context)]
            tiers.extend(
                self._lookup_type_fqn(f"{fqn}.{name}", context)
                for fqn in self._enclosing_type_fqns(owner, context)
            )
            if compilation_unit is not None:
                if compilation_unit.package_fqn:
                    tiers.append(
                        self._lookup_type_fqn(
                            f"{compilation_unit.package_fqn}.{name}", context
                        )
                    )
                qualified_on_demand_types: set[SymbolID] = set()
                for import_id in compilation_unit.import_stmt_ids:
                    import_entity = context.entity_registry.get(import_id)
                    if (
                        isinstance(import_entity, JavaImport)
                        and import_entity.import_kind == "on_demand"
                    ):
                        package_fqn = resolve_java_import(
                            import_entity.import_path, import_entity.import_kind
                        )
                        qualified_on_demand_types.update(
                            self._lookup_type_fqn(f"{package_fqn}.{name}", context)
                        )
                qualified_on_demand_types.update(
                    self._lookup_type_fqn(f"java.lang.{name}", context)
                )
                if qualified_on_demand_types:
                    tiers.append(qualified_on_demand_types)
            else:
                tiers.append(self._lookup_type_fqn(f"java.lang.{name}", context))
            return tiers

        return self._simple_type_candidate_tiers(name, owner, context)

    def _simple_type_candidate_tiers(
        self,
        name: str,
        owner: Entity,
        context: Context,
    ) -> list[set[SymbolID]]:
        compilation_unit = self._get_compilation_unit_for_type(owner, context)
        tiers: list[set[SymbolID]] = []
        tiers.extend(
            self._lookup_type_fqn(f"{fqn}.{name}", context)
            for fqn in self._enclosing_type_fqns(owner, context)
        )
        current_unit_types = self._current_compilation_unit_types(
            compilation_unit, name, context
        )
        if current_unit_types:
            tiers.append(current_unit_types)

        if compilation_unit is not None:
            single_imports: set[SymbolID] = set()
            for import_id in compilation_unit.import_stmt_ids:
                import_entity = context.entity_registry.get(import_id)
                if (
                    isinstance(import_entity, JavaImport)
                    and import_entity.import_kind == "single_type"
                    and import_entity.imported_name == name
                ):
                    single_imports.update(
                        self._lookup_type_fqn(import_entity.import_path, context)
                    )
            if single_imports:
                tiers.append(single_imports)

        package_fqn = getattr(compilation_unit, "package_fqn", None)
        same_package_fqn = f"{package_fqn}.{name}" if package_fqn else name
        same_package_types = self._lookup_type_fqn(same_package_fqn, context)
        if same_package_types:
            tiers.append(same_package_types)

        if compilation_unit is not None:
            on_demand_types: set[SymbolID] = set()
            for import_id in compilation_unit.import_stmt_ids:
                import_entity = context.entity_registry.get(import_id)
                if (
                    isinstance(import_entity, JavaImport)
                    and import_entity.import_kind == "on_demand"
                ):
                    package_fqn = resolve_java_import(
                        import_entity.import_path, import_entity.import_kind
                    )
                    on_demand_types.update(
                        self._lookup_type_fqn(f"{package_fqn}.{name}", context)
                    )
            on_demand_types.update(self._lookup_type_fqn(f"java.lang.{name}", context))
            if on_demand_types:
                tiers.append(on_demand_types)

        return tiers

    def _lookup_member_type_components(
        self,
        parent_ids: set[SymbolID],
        components: list[str],
        context: Context,
    ) -> set[SymbolID]:
        current_ids = parent_ids
        for component in components:
            next_ids: set[SymbolID] = set()
            for parent_id in current_ids:
                parent = context.entity_registry.get(parent_id)
                if not isinstance(parent, TypeDefinition):
                    continue
                for child_id in self._lookup_type_fqn(
                    f"{parent.fqn}.{component}", context
                ):
                    child = context.entity_registry.get(child_id)
                    if (
                        isinstance(child, TypeDefinition)
                        and child.parent_id == parent.id
                        and child.name == component
                    ):
                        next_ids.add(child_id)
            current_ids = next_ids
            if not current_ids:
                break
        return current_ids

    def _type_candidates(
        self,
        raw_name: str,
        owner: Entity,
        context: Context,
    ) -> set[SymbolID]:
        for candidates in self._type_candidate_tiers(raw_name, owner, context):
            if candidates:
                return candidates
        return set()

    def _is_nested_within(
        self,
        candidate: TypeDefinition,
        owner: Entity,
        context: Context,
    ) -> bool:
        current_id = getattr(candidate, "parent_id", None)
        seen: set[SymbolID] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            if current_id == owner.id:
                return True
            current = context.entity_registry.get(current_id)
            if not isinstance(current, TypeDefinition):
                return False
            current_id = getattr(current, "parent_id", None)
        return False

    def _top_level_type(
        self,
        entity: Entity,
        context: Context,
    ) -> TypeDefinition | None:
        if not isinstance(entity, TypeDefinition):
            return None

        top_level = entity
        current: Entity | None = entity
        seen: set[SymbolID] = set()
        while current is not None and current.id not in seen:
            seen.add(current.id)
            if not isinstance(current, TypeDefinition):
                break
            top_level = current
            parent_id = getattr(current, "parent_id", None)
            current = context.entity_registry.get(parent_id) if parent_id else None
        return top_level

    def _is_in_same_nest(
        self,
        candidate: TypeDefinition,
        owner: Entity,
        context: Context,
    ) -> bool:
        candidate_top_level = self._top_level_type(candidate, context)
        owner_top_level = self._top_level_type(owner, context)
        return (
            candidate_top_level is not None
            and owner_top_level is not None
            and candidate_top_level.id == owner_top_level.id
        )

    def _enclosing_types(
        self,
        candidate: TypeDefinition,
        context: Context,
    ) -> list[TypeDefinition]:
        enclosing: list[TypeDefinition] = []
        current_id = getattr(candidate, "parent_id", None)
        seen: set[SymbolID] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            current = context.entity_registry.get(current_id)
            if not isinstance(current, TypeDefinition):
                break
            enclosing.append(current)
            current_id = getattr(current, "parent_id", None)
        return enclosing

    def _type_package(
        self,
        entity: TypeDefinition,
        context: Context,
    ) -> str | None:
        compilation_unit = self._get_compilation_unit_for_type(entity, context)
        if compilation_unit is not None:
            return compilation_unit.package_fqn
        fqn = getattr(entity, "fqn", "")
        return fqn.rsplit(".", 1)[0] if "." in fqn else None

    def _is_type_visible(
        self,
        candidate: TypeDefinition,
        owner: Entity,
        context: Context,
        module_index,
    ) -> bool:
        requester_unit = self._get_compilation_unit_for_type(owner, context)
        requester_module = module_index.cu_to_module.get(
            getattr(requester_unit, "id", "")
        )
        fqn = getattr(candidate, "fqn", None)
        if not fqn or not is_visible(requester_module, fqn, module_index):
            return False

        if any(
            not self._is_type_visible(enclosing, owner, context, module_index)
            for enclosing in self._enclosing_types(candidate, context)
        ):
            return False

        parent_id = getattr(candidate, "parent_id", None)
        parent = context.entity_registry.get(parent_id) if parent_id else None
        visibility = getattr(candidate, "visibility", None) or "package-private"
        if isinstance(parent, JavaInterface):
            visibility = "public"
        if visibility == "public":
            return True

        requester_package = getattr(requester_unit, "package_fqn", None)
        candidate_package = self._type_package(candidate, context)
        if visibility in ("package-private", "protected"):
            return candidate_package == requester_package or (
                visibility == "protected"
                and self._is_nested_within(candidate, owner, context)
            )
        if visibility == "private":
            return self._is_in_same_nest(candidate, owner, context)
        return candidate_package == requester_package

    def _type_resolution_result(
        self,
        raw_name: str,
        owner: Entity,
        context: Context,
        candidates: set[SymbolID],
    ) -> ResolutionResult[SymbolID]:
        module_index = build_module_index(context.entity_registry)
        visible: list[SymbolID] = []
        inaccessible: list[SymbolID] = []
        for entity_id in sorted(candidates):
            entity = context.entity_registry.get(entity_id)
            if isinstance(entity, TypeDefinition) and self._is_type_visible(
                entity, owner, context, module_index
            ):
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

    def _resolve_type_name(
        self,
        raw_name: str,
        owner: Entity,
        context: Context,
    ) -> ResolutionResult[SymbolID]:
        if "." in raw_name.strip():
            name = raw_name.strip()
            leading_name = name.split(".", 1)[0]
            leading_result = self._resolve_type_name(leading_name, owner, context)
            if leading_result.status is not ResolutionStatus.UNRESOLVED:
                if leading_result.status is ResolutionStatus.AMBIGUOUS:
                    components = name.split(".")
                    member_candidates = self._lookup_member_type_components(
                        set(leading_result.candidates), components[1:], context
                    )
                    if member_candidates:
                        return ResolutionResult(
                            status=ResolutionStatus.AMBIGUOUS,
                            candidates=tuple(sorted(member_candidates)),
                            reason=leading_result.reason,
                        )
                if leading_result.status is not ResolutionStatus.RESOLVED:
                    return ResolutionResult(
                        status=leading_result.status,
                        candidates=leading_result.candidates,
                        reason=leading_result.reason,
                    )
                if leading_result.value is None:
                    return ResolutionResult(
                        status=ResolutionStatus.UNRESOLVED,
                        reason=f"No type found for '{name}'",
                    )
                components = name.split(".")
                member_candidates = self._lookup_member_type_components(
                    {leading_result.value}, components[1:], context
                )
                if not member_candidates:
                    return ResolutionResult(
                        status=ResolutionStatus.UNRESOLVED,
                        reason=f"No member type found for '{name}'",
                    )
                return self._type_resolution_result(
                    name, owner, context, member_candidates
                )

        candidates = self._type_candidates(raw_name, owner, context)
        if not candidates:
            return ResolutionResult(
                status=ResolutionStatus.UNRESOLVED,
                reason=f"No type found for '{raw_name}'",
            )
        return self._type_resolution_result(raw_name, owner, context, candidates)

    def resolve_type_reference(
        self,
        raw_name: str,
        owner: TypeDefinition,
        context: Context,
    ) -> ResolutionResult[SymbolID]:
        return self._resolve_type_name(raw_name, owner, context)

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
                    reason=(
                        f"Multiple symbols found for '{symbol_name}'"
                        if len(cached_resolved) > 1
                        else None
                    ),
                )

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
                reason=(
                    f"Expected one compilation unit for '{compilation_unit_fqn}', "
                    f"found {len(compilation_units)}"
                ),
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

        type_result = self._resolve_type_name(symbol_name, compilation_unit, context)
        if type_result.status != ResolutionStatus.UNRESOLVED:
            type_resolved_ids: set[SymbolID] = set()
            type_inaccessible_ids: set[SymbolID] = set()
            type_ambiguous_ids: set[SymbolID] = set()
            if type_result.status == ResolutionStatus.RESOLVED:
                if type_result.value is not None:
                    type_resolved_ids.add(type_result.value)
            elif type_result.status == ResolutionStatus.AMBIGUOUS:
                type_resolved_ids.update(type_result.candidates)
                type_ambiguous_ids.update(type_result.candidates)
            else:
                type_inaccessible_ids.update(type_result.candidates)
            result = JavaResolverResult(
                resolved_ids=type_resolved_ids,
                unresolved_ids=set(),
                inaccessible_ids=type_inaccessible_ids,
                ambiguous_ids=type_ambiguous_ids,
                reason=type_result.reason,
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

        resolved_ids: set[SymbolID] = set()
        unresolved_ids: set[SymbolID] = set()
        inaccessible_ids: set[SymbolID] = set()
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
            reason=(
                f"Multiple symbols found for '{symbol_name}'"
                if len(resolved_ids) > 1
                else (
                    f"Symbol '{symbol_name}' is inaccessible"
                    if inaccessible_ids and not resolved_ids
                    else (
                        f"No symbol found for '{symbol_name}'"
                        if not resolved_ids
                        else None
                    )
                )
            ),
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
