import logging

from deproc.core.context import Context
from deproc.core.interfaces.parser.models import Entity
from deproc.core.interfaces.resolver import Resolver

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

    def _resolve_base_ids(self, cls: PythonClass, context: Context) -> list[SymbolID]:
        module = self._get_module(cls.id, context)
        if module is None:
            return []

        base_ids: list[SymbolID] = []
        for base_name in cls.inherits:
            base_name = base_name.split("[", 1)[0].strip()
            if not base_name:
                continue
            resolved_ids = context.entity_registry.get_ids_by_fqn(base_name)
            if not resolved_ids:
                if "." in base_name:
                    base_module, base_symbol = base_name.rsplit(".", 1)
                    resolved_ids, _ = self.resolve_symbol(
                        base_module, base_symbol, context
                    )
                else:
                    resolved_ids, _ = self.resolve_symbol(
                        module.fqn, base_name, context
                    )
            for base_id in sorted(resolved_ids):
                if isinstance(self._get_symbol(base_id, context), PythonClass):
                    base_ids.append(base_id)
        return base_ids

    def _class_mro_ids(
        self,
        class_id: SymbolID,
        context: Context,
        memo: dict[SymbolID, list[SymbolID] | None],
        active: set[SymbolID],
    ) -> list[SymbolID] | None:
        if class_id in memo:
            return memo[class_id]
        if class_id in active:
            return None

        cls = self._get_symbol(class_id, context)
        if not isinstance(cls, PythonClass):
            memo[class_id] = None
            return None
        active.add(class_id)
        base_ids = self._resolve_base_ids(cls, context)
        if cls.inherits and not base_ids:
            active.remove(class_id)
            memo[class_id] = None
            return None
        if not base_ids:
            active.remove(class_id)
            memo[class_id] = [class_id]
            return memo[class_id]

        base_mros: dict[str, list[str] | None] = {}
        base_fqns: list[str] = []
        for base_id in base_ids:
            base = self._get_symbol(base_id, context)
            base_fqn = getattr(base, "fqn", None)
            if not base_fqn or base_fqn in base_mros:
                continue
            base_mro_ids = self._class_mro_ids(base_id, context, memo, active)
            if base_mro_ids is None:
                active.remove(class_id)
                memo[class_id] = None
                return None
            base_mros[base_fqn] = [
                getattr(self._get_symbol(mro_id, context), "fqn", "")
                for mro_id in base_mro_ids
            ]
            base_fqns.append(base_fqn)

        mro_fqns = compute_mro_from_bases(cls.fqn, base_mros, base_fqns)
        if mro_fqns is None:
            active.remove(class_id)
            memo[class_id] = None
            return None

        mro_ids: list[SymbolID] = []
        for mro_fqn in mro_fqns:
            if mro_fqn == cls.fqn:
                mro_ids.append(class_id)
                continue
            candidates = [
                candidate_id
                for candidate_id in context.entity_registry.get_ids_by_fqn(mro_fqn)
                if isinstance(self._get_symbol(candidate_id, context), PythonClass)
            ]
            if len(candidates) != 1:
                active.remove(class_id)
                memo[class_id] = None
                return None
            mro_ids.append(candidates[0])

        active.remove(class_id)
        memo[class_id] = mro_ids
        return mro_ids

    def resolve(
        self, module_fqn: str, symbol_name: str, context: Context
    ) -> PythonResolverResult:
        resolved_ids, unresolved_ids = self.resolve_symbol(
            module_fqn, symbol_name, context
        )
        return PythonResolverResult(
            resolved_ids=resolved_ids, unresolved_ids=unresolved_ids
        )
