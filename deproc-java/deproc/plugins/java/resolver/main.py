import logging

from deproc.core.context import Context
from deproc.core.interfaces.resolver import Resolver

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
    def _get_compilation_unit(
        self,
        compilation_unit_fqn: str,
        context: Context,
    ) -> JavaCompilationUnit | None:
        ids = context.entity_registry.get_ids_by_fqn(compilation_unit_fqn)
        for entity_id in ids:
            entity = context.entity_registry.get(entity_id)
            if isinstance(entity, JavaCompilationUnit):
                return entity
        return None

    def _lookup_fqn(self, fqn: str, context: Context) -> set[SymbolID]:
        return context.entity_registry.get_ids_by_fqn(fqn)

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
                return JavaResolverResult(
                    resolved_ids=set(cached[0]),
                    unresolved_ids=set(cached[1]),
                    inaccessible_ids=set(cached[2]),
                )

        resolved_ids: set[SymbolID] = set()
        unresolved_ids: set[SymbolID] = set()
        inaccessible_ids: set[SymbolID] = set()

        compilation_unit = self._get_compilation_unit(compilation_unit_fqn, context)
        if compilation_unit is None:
            logger.warning(
                f"Compilation unit not found for FQN: {compilation_unit_fqn}"
            )
            result = JavaResolverResult(
                resolved_ids=set(),
                unresolved_ids=set(),
                inaccessible_ids=set(),
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
