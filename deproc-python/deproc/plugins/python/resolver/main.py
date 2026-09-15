import logging
from collections.abc import Mapping

from deproc.core.context import Context
from deproc.core.interfaces.parser.models import Entity
from deproc.core.interfaces.resolver import ResolutionStatus, Resolver

from ..parser.models import (
    PythonClass,
    PythonImportAlias,
    PythonImportStatement,
    PythonModule,
    SymbolID,
)
from ..utils.exports import build_module_exports, get_dynamic_export_modules
from ..utils.imports import resolve_relative_import_path
from ..utils.mro import compute_mro_from_bases
from .models import (
    PythonBaseResolution,
    PythonClassMROResult,
    PythonInheritedMember,
    PythonInheritedMembersResult,
    PythonResolverResult,
    ResolvedIDs,
    UnresolvedIDs,
)

logger = logging.getLogger(__name__)


class PythonResolver(Resolver[PythonResolverResult]):
    def _get_symbol(self, symbol_id: SymbolID, context: Context) -> Entity | None:
        symbol = context.entity_registry.get(symbol_id)
        if not symbol:
            logger.warning(f"Symbol not found for ID: {symbol_id}")
            return None
        return symbol

    def _get_module(self, symbol_id: SymbolID, context: Context) -> PythonModule | None:
        seen: set[SymbolID] = set()
        current_id: SymbolID | None = symbol_id
        while current_id and current_id not in seen:
            seen.add(current_id)
            symbol = self._get_symbol(current_id, context)
            if not symbol:
                return None
            if isinstance(symbol, PythonModule):
                return symbol
            current_id = getattr(symbol, "parent_id", None)
        return None

    def _get_target_module_fqn(
        self, import_statement_id: SymbolID, context: Context
    ) -> str | None:
        import_statement = self._get_symbol(import_statement_id, context)
        if not import_statement:
            return None

        path = getattr(import_statement, "path", None)

        # Handle relative imports
        if path and path.startswith("."):
            parent_module = self._get_module(import_statement_id, context)
            if parent_module:
                parent_fqn = parent_module.fqn
                if parent_fqn:
                    is_package = getattr(parent_module, "path", "").endswith(
                        ("__init__.py", "__init__.pyi")
                    )
                    return resolve_relative_import_path(path, parent_fqn, is_package)

        return path

    def _extract_alias_ids(
        self, symbol_ids: set[SymbolID], context: Context
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        alias_ids = set()
        non_alias_ids = set()

        for symbol_id in symbol_ids:
            symbol = self._get_symbol(symbol_id, context)
            if isinstance(symbol, PythonImportAlias):
                alias_ids.add(symbol_id)
            else:
                non_alias_ids.add(symbol_id)

        return alias_ids, non_alias_ids

    def _populate_cache(
        self,
        module_fqn: str,
        symbol_name: str,
        resolved_ids: ResolvedIDs,
        unresolved_ids: UnresolvedIDs,
        cache,
    ):
        if cache:
            cache.set(module_fqn, symbol_name, resolved_ids, unresolved_ids)

    def _populate_module_cache_key_maps(
        self,
        module_fqn: str,
        cache_keys: set[tuple[str, str]],
        cache,
    ):
        if cache:
            cache.add_cache_keys_for_module(module_fqn, cache_keys)

    def _populate_module_cache_key_maps_for_cached_result(
        self,
        module_fqn: str,
        symbol_name: str,
        cache_keys: set[tuple[str, str]] | None,
        cache,
    ):
        if not cache_keys:
            return

        current_cache_key = (module_fqn, symbol_name)
        module_fqns = cache.get_modules_for_cache_key(current_cache_key)

        for cache_key in cache_keys:
            cache.add_modules_for_cache_key(cache_key, module_fqns)

    def get_ids_by_fqn(
        self, module_fqn: str, symbol_name: str, context: Context
    ) -> set[SymbolID]:
        return context.entity_registry.get_ids_by_fqn(f"{module_fqn}.{symbol_name}")

    def resolve_symbol(
        self,
        module_fqn: str,
        symbol_name: str,
        context: Context,
        visited: set[SymbolID] | None = None,
        cache_keys: set[tuple[str, str]] | None = None,
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        if cache_keys is None:
            cache_keys = set()
        if visited is None:
            visited = set()
        current_cache_key = (module_fqn, symbol_name)
        if current_cache_key in cache_keys:
            return set(), set()
        cache_keys.add(current_cache_key)

        symbol_cache = context.get_symbol_cache("python")
        if symbol_cache:
            cached_result = symbol_cache.get(module_fqn, symbol_name)
            if cached_result is not None:
                self._populate_module_cache_key_maps_for_cached_result(
                    module_fqn, symbol_name, cache_keys, symbol_cache
                )
                return cached_result

        resolved_ids = self.get_ids_by_fqn(module_fqn, symbol_name, context)
        if not resolved_ids:
            resolved_ids, unresolved_ids = self._resolve_wildcard_imports(
                module_fqn, symbol_name, context, visited, cache_keys
            )
            if not resolved_ids and not unresolved_ids:
                logger.warning(
                    f"Symbols not found for module: {module_fqn}, symbol: {symbol_name}, caching empty sets"
                )
            self._populate_cache(
                module_fqn, symbol_name, resolved_ids, unresolved_ids, symbol_cache
            )
            self._populate_module_cache_key_maps(module_fqn, cache_keys, symbol_cache)
            return resolved_ids, unresolved_ids

        found_alias_ids, resolved_ids = self._extract_alias_ids(resolved_ids, context)
        unresolved_ids = set()

        if found_alias_ids:
            resolved_alias_ids, unresolved_ids = self.resolve_alias_ids(
                found_alias_ids, context, visited, cache_keys
            )
            resolved_ids.update(resolved_alias_ids)

        self._populate_cache(
            module_fqn, symbol_name, resolved_ids, unresolved_ids, symbol_cache
        )
        self._populate_module_cache_key_maps(module_fqn, cache_keys, symbol_cache)
        return resolved_ids, unresolved_ids

    def _resolve_wildcard_imports(
        self,
        module_fqn: str,
        symbol_name: str,
        context: Context,
        visited: set[SymbolID] | None,
        cache_keys: set[tuple[str, str]],
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        module_ids = context.entity_registry.get_ids_by_fqn(module_fqn)
        resolved_ids = set()
        unresolved_ids = set()
        module_exports = build_module_exports(context.entity_registry)
        dynamic_modules = get_dynamic_export_modules(context.entity_registry)

        for module_id in module_ids:
            module = self._get_symbol(module_id, context)
            if not isinstance(module, PythonModule):
                continue

            for import_id in module.import_stmt_ids:
                import_stmt = self._get_symbol(import_id, context)
                if not isinstance(import_stmt, PythonImportStatement):
                    continue
                if not import_stmt.wildcard:
                    continue

                target_module_fqn = self._get_target_module_fqn(import_id, context)
                if not target_module_fqn:
                    continue
                target_ids = context.entity_registry.get_ids_by_fqn(target_module_fqn)
                target_modules = [
                    self._get_symbol(target_id, context) for target_id in target_ids
                ]
                self._populate_module_cache_key_maps(
                    target_module_fqn,
                    {(module_fqn, symbol_name)},
                    context.get_symbol_cache("python"),
                )
                if target_module_fqn in dynamic_modules:
                    unresolved_ids.add(import_id)
                    continue
                if target_module_fqn not in module_exports:
                    continue
                if symbol_name not in module_exports[target_module_fqn]:
                    continue
                if not target_modules:
                    unresolved_ids.add(import_id)
                    continue

                target_cache_key = (target_module_fqn, symbol_name)
                if target_cache_key in cache_keys:
                    continue
                resolved, unresolved = self.resolve_symbol(
                    target_module_fqn,
                    symbol_name,
                    context,
                    visited,
                    cache_keys,
                )
                resolved_ids.update(resolved)
                unresolved_ids.update(unresolved)

        return resolved_ids, unresolved_ids

    def resolve_alias_ids(
        self,
        alias_ids: set[SymbolID],
        context: Context,
        visited: set[SymbolID] | None = None,
        cache_keys: set[tuple[str, str]] | None = None,
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        if visited is None:
            visited = set()

        if not alias_ids:
            return set(), set()

        resolved_ids = set()
        unresolved_ids = set()
        for symbol_id in alias_ids:
            # Handle worst case circular import scenario explicitly
            if symbol_id in visited:
                continue
            visited.add(symbol_id)

            symbol = self._get_symbol(symbol_id, context)
            if isinstance(symbol, PythonImportAlias):
                resolved_ids_from_alias, unresolved_ids_from_alias = self.resolve_alias(
                    symbol, context, visited, cache_keys
                )
                if resolved_ids_from_alias:
                    resolved_ids.update(resolved_ids_from_alias)
                    unresolved_ids.update(unresolved_ids_from_alias)
                else:
                    unresolved_ids.add(symbol_id)
            else:
                resolved_ids.add(symbol_id)

        return resolved_ids, unresolved_ids

    def resolve_alias(
        self,
        alias: PythonImportAlias,
        context: Context,
        visited: set[SymbolID] | None = None,
        cache_keys: set[tuple[str, str]] | None = None,
    ) -> tuple[ResolvedIDs, UnresolvedIDs]:
        import_statement_id = alias.parent_id
        if import_statement_id is None:
            return set(), set()

        import_name = alias.name
        import_statement = self._get_symbol(import_statement_id, context)
        target_module_path = self._get_target_module_fqn(import_statement_id, context)

        if (
            isinstance(import_statement, PythonImportStatement)
            and import_statement.type == "generic_import"
            and alias.import_path is not None
        ):
            target_module_path = alias.import_path or target_module_path
            if not target_module_path:
                return set(), set()
            self._populate_module_cache_key_maps(
                target_module_path,
                cache_keys or set(),
                context.get_symbol_cache("python"),
            )
            resolved_ids = context.entity_registry.get_ids_by_fqn(target_module_path)
            return resolved_ids, set()

        if not target_module_path:
            logger.warning(f"Target module path not found for alias: {alias.name}")
            return set(), set()

        resolved_ids, unresolved_ids = self.resolve_symbol(
            target_module_path, import_name, context, visited, cache_keys
        )
        return resolved_ids, unresolved_ids

    @staticmethod
    def _normalize_base_name(base_name: str) -> str:
        return base_name.split("[", 1)[0].strip()

    def _resolve_base(
        self,
        cls: PythonClass,
        base_name: str,
        context: Context,
        base_overrides: Mapping[tuple[SymbolID, str], SymbolID] | None = None,
    ) -> PythonBaseResolution:
        normalized_name = self._normalize_base_name(base_name)
        override_id = (base_overrides or {}).get((cls.id, normalized_name))
        if override_id:
            override = self._get_symbol(override_id, context)
            if isinstance(override, PythonClass):
                return PythonBaseResolution(
                    name=base_name,
                    status=ResolutionStatus.RESOLVED,
                    resolved_id=override_id,
                    candidates=(override_id,),
                )

        resolved_ids = context.entity_registry.get_ids_by_fqn(normalized_name)
        unresolved_ids: set[SymbolID] = set()
        if not resolved_ids:
            module = self._get_module(cls.id, context)
            if module is None:
                return PythonBaseResolution(
                    name=base_name,
                    status=ResolutionStatus.UNRESOLVED,
                    reason=f"containing module not found for base {base_name}",
                )
            if "." in normalized_name:
                base_module, base_symbol = normalized_name.rsplit(".", 1)
                resolved_ids, unresolved_ids = self.resolve_symbol(
                    base_module, base_symbol, context
                )
            else:
                resolved_ids, unresolved_ids = self.resolve_symbol(
                    module.fqn, normalized_name, context
                )

        class_ids = tuple(
            sorted(
                symbol_id
                for symbol_id in resolved_ids
                if isinstance(self._get_symbol(symbol_id, context), PythonClass)
            )
        )
        if len(class_ids) == 1:
            return PythonBaseResolution(
                name=base_name,
                status=ResolutionStatus.RESOLVED,
                resolved_id=class_ids[0],
                candidates=class_ids,
            )
        if len(class_ids) > 1:
            return PythonBaseResolution(
                name=base_name,
                status=ResolutionStatus.AMBIGUOUS,
                candidates=class_ids,
                reason=f"ambiguous Python base {base_name}",
            )

        reason = f"Python base {base_name} was not resolved"
        if unresolved_ids:
            reason = f"Python base {base_name} has unresolved import candidates"
        return PythonBaseResolution(
            name=base_name,
            status=ResolutionStatus.UNRESOLVED,
            reason=reason,
        )

    def _resolve_base_resolutions(
        self,
        cls: PythonClass,
        context: Context,
        base_overrides: Mapping[tuple[SymbolID, str], SymbolID] | None = None,
    ) -> tuple[PythonBaseResolution, ...]:
        return tuple(
            self._resolve_base(cls, base_name, context, base_overrides)
            for base_name in cls.inherits
            if self._normalize_base_name(base_name)
        )

    def _mro_ids_from_fqns(
        self,
        class_id: SymbolID,
        mro_fqns: list[str],
        context: Context,
        known_ids: Mapping[str, SymbolID | None] | None = None,
    ) -> list[SymbolID] | None:
        cls = self._get_symbol(class_id, context)
        if not isinstance(cls, PythonClass):
            return None

        mro_ids: list[SymbolID] = []
        for mro_fqn in mro_fqns:
            if mro_fqn == cls.fqn:
                mro_ids.append(class_id)
                continue
            if known_ids and mro_fqn in known_ids:
                known_id = known_ids[mro_fqn]
                if known_id is None:
                    return None
                mro_ids.append(known_id)
                continue
            candidates = [
                candidate_id
                for candidate_id in context.entity_registry.get_ids_by_fqn(mro_fqn)
                if isinstance(self._get_symbol(candidate_id, context), PythonClass)
            ]
            if len(candidates) != 1:
                return None
            mro_ids.append(candidates[0])
        return mro_ids

    def resolve_class_mro(
        self,
        class_id: SymbolID,
        context: Context,
        base_overrides: Mapping[tuple[SymbolID, str], SymbolID] | None = None,
    ) -> PythonClassMROResult:
        return self._resolve_class_mro(
            class_id, context, {}, set(), base_overrides or {}
        )

    def _resolve_class_mro(
        self,
        class_id: SymbolID,
        context: Context,
        memo: dict[SymbolID, PythonClassMROResult],
        active: set[SymbolID],
        base_overrides: Mapping[tuple[SymbolID, str], SymbolID],
    ) -> PythonClassMROResult:
        if class_id in memo:
            return memo[class_id]
        if class_id in active:
            return PythonClassMROResult(
                status=ResolutionStatus.UNRESOLVED,
                mro_ids=(class_id,),
                reason="cyclic Python inheritance",
            )

        cls = self._get_symbol(class_id, context)
        if not isinstance(cls, PythonClass):
            return PythonClassMROResult(
                status=ResolutionStatus.UNRESOLVED,
                reason=f"entity {class_id} is not a Python class",
            )

        active.add(class_id)
        bases = self._resolve_base_resolutions(cls, context, base_overrides)
        if not bases:
            result = PythonClassMROResult(
                status=ResolutionStatus.RESOLVED,
                mro_ids=(class_id,),
            )
            memo[class_id] = result
            active.remove(class_id)
            return result

        base_mros: dict[str, list[str] | None] = {}
        base_fqns: list[str] = []
        known_mro_ids: dict[str, SymbolID | None] = {cls.fqn: class_id}
        failure_status: ResolutionStatus | None = None
        failure_reason: str | None = None

        for base in bases:
            if base.status is not ResolutionStatus.RESOLVED or base.resolved_id is None:
                failure_status = base.status
                failure_reason = base.reason
                break

            base_entity = self._get_symbol(base.resolved_id, context)
            base_fqn = getattr(base_entity, "fqn", None)
            if not base_fqn:
                failure_status = ResolutionStatus.UNRESOLVED
                failure_reason = f"resolved base {base.name} has no FQN"
                break

            base_result = self._resolve_class_mro(
                base.resolved_id,
                context,
                memo,
                active,
                base_overrides,
            )
            base_mro_fqns = [
                getattr(self._get_symbol(mro_id, context), "fqn", "")
                for mro_id in base_result.mro_ids
            ]
            for mro_id, mro_fqn in zip(base_result.mro_ids, base_mro_fqns, strict=True):
                if mro_fqn in known_mro_ids and known_mro_ids[mro_fqn] != mro_id:
                    known_mro_ids[mro_fqn] = None
                else:
                    known_mro_ids[mro_fqn] = mro_id
            base_mros[base_fqn] = base_mro_fqns
            base_fqns.append(base_fqn)
            if base_result.status is not ResolutionStatus.RESOLVED:
                failure_status = base_result.status
                failure_reason = base_result.reason
                break

        mro_fqns = compute_mro_from_bases(cls.fqn, base_mros, base_fqns)
        if mro_fqns is None:
            result = PythonClassMROResult(
                status=failure_status or ResolutionStatus.UNRESOLVED,
                mro_ids=(class_id,),
                bases=bases,
                reason=failure_reason or f"inconsistent MRO for {cls.fqn}",
            )
        else:
            mro_ids = self._mro_ids_from_fqns(
                class_id, mro_fqns, context, known_mro_ids
            )
            if mro_ids is None:
                result = PythonClassMROResult(
                    status=ResolutionStatus.AMBIGUOUS,
                    mro_ids=(class_id,),
                    bases=bases,
                    reason=f"ambiguous Python MRO for {cls.fqn}",
                )
            else:
                result = PythonClassMROResult(
                    status=failure_status or ResolutionStatus.RESOLVED,
                    mro_ids=tuple(mro_ids),
                    bases=bases,
                    reason=failure_reason,
                )

        memo[class_id] = result
        active.remove(class_id)
        return result

    def get_inherited_members(
        self,
        class_id: SymbolID,
        context: Context,
        mro_result: PythonClassMROResult | None = None,
    ) -> PythonInheritedMembersResult:
        result = mro_result or self.resolve_class_mro(class_id, context)
        if not result.mro_ids:
            return PythonInheritedMembersResult(
                status=result.status,
                reason=result.reason,
            )

        cls = self._get_symbol(class_id, context)
        if not isinstance(cls, PythonClass):
            return PythonInheritedMembersResult(
                status=ResolutionStatus.UNRESOLVED,
                mro_ids=result.mro_ids,
                reason=f"entity {class_id} is not a Python class",
            )

        own_ids = [*cls.method_ids, *cls.property_ids, *cls.inner_type_ids]
        seen_names = {
            getattr(self._get_symbol(member_id, context), "name", "")
            for member_id in own_ids
        }
        members: list[PythonInheritedMember] = []
        for depth, owner_id in enumerate(result.mro_ids[1:], 1):
            owner = self._get_symbol(owner_id, context)
            if not isinstance(owner, PythonClass):
                continue
            member_ids = [
                *owner.method_ids,
                *owner.property_ids,
                *owner.inner_type_ids,
            ]
            for member_id in member_ids:
                member = self._get_symbol(member_id, context)
                name = getattr(member, "name", "") if member else ""
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                members.append(
                    PythonInheritedMember(
                        member_id=member_id,
                        owner_id=owner_id,
                        name=name,
                        mro_depth=depth,
                    )
                )

        return PythonInheritedMembersResult(
            status=result.status,
            mro_ids=result.mro_ids,
            members=tuple(members),
            reason=result.reason,
        )

    def _class_mro_ids(
        self,
        class_id: SymbolID,
        context: Context,
        memo: dict[SymbolID, list[SymbolID] | None],
        active: set[SymbolID],
    ) -> list[SymbolID] | None:
        if class_id in memo:
            return memo[class_id]
        result = self.resolve_class_mro(class_id, context)
        mro_ids = (
            list(result.mro_ids) if result.status is ResolutionStatus.RESOLVED else None
        )
        memo[class_id] = mro_ids
        return mro_ids

    def resolve(
        self, module_fqn: str, symbol_name: str, context: Context
    ) -> PythonResolverResult:
        resolved_ids, unresolved_ids = self.resolve_symbol(
            module_fqn, symbol_name, context
        )
        ambiguous_ids = resolved_ids if len(resolved_ids) > 1 else set()
        if ambiguous_ids:
            reason = f"Multiple symbols found for '{module_fqn}.{symbol_name}'"
        elif not resolved_ids:
            reason = f"No symbol found for '{module_fqn}.{symbol_name}'"
        else:
            reason = None
        return PythonResolverResult(
            resolved_ids=resolved_ids,
            unresolved_ids=unresolved_ids,
            ambiguous_ids=ambiguous_ids,
            reason=reason,
        )
