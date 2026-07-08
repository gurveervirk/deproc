from collections import defaultdict
from deproc.core.interfaces.symbol_table_builder import SymbolTableBuilder
from deproc.core.context import Context
from ..linker.models import PythonModule
from .models import (
    PythonModuleSymbolMap,
    PythonSymbolTable
)

class PythonSymbolTableBuilder(SymbolTableBuilder):
    def _process_control_flow_group_for_imports(self, group_id: str, symbol_map: dict[str, list[str]], context: Context):
        group = context.entity_registry.get(group_id)
        if not group:
            return
        
        for block_id in getattr(group, "block_ids", []):
            block = context.entity_registry.get(block_id)
            if not block:
                continue
            
            for import_stmt_id in getattr(block, "import_stmt_ids", []):
                import_stmt = context.entity_registry.get(import_stmt_id)
                if import_stmt and hasattr(import_stmt, "name_ids"):
                    for name_id in import_stmt.name_ids:
                        import_alias_entity = context.entity_registry.get(name_id)
                        if import_alias_entity:
                            symbol_map[import_alias_entity.alias or import_alias_entity.name].append(name_id)
            
            # Recursively process nested control flow groups
            for nested_group_id in getattr(block, "nested_group_ids", []):
                self._process_control_flow_group_for_imports(nested_group_id, symbol_map, context)
    
    def create_symbol_map_for_module(
        self,
        module: PythonModule,
        module_fqn: str,
        context: Context
    ) -> PythonModuleSymbolMap:
        symbol_map: PythonModuleSymbolMap = defaultdict(set)
        for entity in context.entity_registry.values():
            # Find all immediately nested entities within the module
            if hasattr(entity, "fqn") and entity.fqn.startswith(module_fqn) and entity.fqn != module_fqn and not entity.fqn[len(module_fqn):].find("."):
                relative_fqn = entity.fqn[len(module_fqn):].lstrip(".")
                if relative_fqn:
                    top_level_symbol = relative_fqn.split(".")[0]
                    symbol_map[top_level_symbol].add(entity.id)

        # Process direct children of the module first
        for import_stmt_id in module.import_stmt_ids:
            import_stmt = context.entity_registry.get(import_stmt_id)
            if import_stmt and hasattr(import_stmt, "name_ids"):
                for name_id in import_stmt.name_ids:
                    import_alias_entity = context.entity_registry.get(name_id)
                    if import_alias_entity:
                        symbol_map[import_alias_entity.alias or import_alias_entity.name].add(name_id)
        
        # Process module's control flow blocks for import statements
        for group_id in module.control_flow_group_ids:
            self._process_control_flow_group_for_imports(group_id, symbol_map, context)

        # Order symbol map lists by line number precedence in the module's source code
        for symbol, ids in symbol_map.items():
            symbol_map[symbol] = sorted(ids, key=lambda x: context.entity_registry.get(x, {}).get('lineno', 0))

        return symbol_map

    def build(self, context: Context) -> PythonSymbolTable:
        """
        Create symbol maps for all modules in the context.
        """
        module_symbol_maps = {}
        for entity in context.entity_registry.values():
            if isinstance(entity, PythonModule):
                module_symbol_maps[entity.fqn] = self.create_symbol_map_for_module(entity, entity.fqn, context)
        symbol_table = PythonSymbolTable(module_symbol_maps=module_symbol_maps)

        context.set_symbol_table(symbol_table)
        return symbol_table