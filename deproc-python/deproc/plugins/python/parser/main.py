from deproc.core.interfaces import SourceParser
from deproc.core.context import Context
from deproc.utils import iter_children, first_child
from tree_sitter import Query, Node, QueryCursor
import os

from .models import (
    Annotation,
    ControlFlowBlock,
    ControlFlowGroup,
    PythonFunctionLike,
    PythonClass,
    PythonImportStatement,
    PythonImportAlias,
    PythonSourceFile,
    SymbolID,
    generate_id
)
from .utils.misc import visibility_from_name
from .utils.extraction import (
    collect_from_assignment_node,
    extract_decorator_details,
    extract_docstring_range,
    extract_signature,
)
from .utils.tree_sitter_python import (
    create_source_range,
    get_python_language,
    get_python_parser,
    node_text
)


class PythonSourceParser(SourceParser):
    def __init__(self):
        self._parser = get_python_parser()
        self._language = get_python_language()

        self.all_exports_query = Query(
            self._language,
            """
            (expression_statement
                (assignment
                    left: (identifier) @all_name (#eq? @all_name "__all__")
                    right: [(list) (tuple)] @all_values
                )
            )"""
        )

    def _compute_fqn(self, file_path: str, context: Context) -> str:
        base_path = context.base_path
        relative_path = os.path.relpath(file_path, base_path)
        without_extension = os.path.splitext(relative_path)[0]
        fqn = without_extension.replace(os.sep, ".")
        return fqn

    def parse_file(self, path: str, context: Context) -> PythonSourceFile:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        if not path.endswith((".py", ".pyi")):
            raise ValueError(f"Unsupported file extension for Python parser: {path}")
        
        source_bytes = open(path, "rb").read()
        tree = self._parser.parse(source_bytes)
        root_node = tree.root_node

        docstring_range = extract_docstring_range(root_node)

        relative_path = os.path.relpath(path, context.base_path).replace("\\", "/")

        source_file = PythonSourceFile(
            path=relative_path,
            docstring_range=docstring_range,
            source=source_bytes.decode("utf-8"),
        )

        parent_fqn = self._compute_fqn(path, context)
        
        source_file.type_ids = self._extract_classes(root_node, context, parent_id=source_file.id, parent_fqn=parent_fqn)
        source_file.function_ids = self._extract_functions(root_node, context, type="FUNCTION", parent_id=source_file.id, parent_fqn=parent_fqn)
        source_file.variable_ids = self._extract_variables(root_node, context, parent_id=source_file.id, parent_fqn=parent_fqn)
        source_file.import_stmt_ids = self._extract_import_statements(root_node, context, parent_id=source_file.id)
        source_file.all_exports = self._extract_all_exports(root_node)
        source_file.control_flow_group_ids = self._extract_control_flow_groups(root_node, context, parent_id=source_file.id, parent_fqn=parent_fqn)

        context.entity_registry.add(source_file)
        return source_file
    
    def _extract_classes(self, root: Node, context: Context, parent_id: SymbolID | None = None, parent_fqn: str | None = None) -> list[SymbolID]:
        return self._traverse_block_for_classes(root, context, parent_id, parent_fqn)
    
    def _traverse_block_for_classes(self, block_node: Node, context: Context, parent_id: SymbolID | None = None, parent_fqn: str | None = None) -> list[SymbolID]:
        class_ids = []

        for child in iter_children(block_node):
            if child.type == "class_definition":
                class_ids.append(self._process_class_node(child, [], context, parent_id, parent_fqn))
            elif child.type == "decorated_definition":
                definition = child.child_by_field_name("definition")
                if definition and definition.type == "class_definition":
                    decorator_details = extract_decorator_details(child)
                    class_ids.append(self._process_class_node(definition, decorator_details, context, parent_id, parent_fqn))

        return class_ids
    
    def _process_class_node(
        self,
        node: Node,
        decorator_details: list[Annotation],
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None
    ) -> SymbolID:
        source_range = create_source_range(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)

        bases_node = node.child_by_field_name("superclasses")
        bases = []
        if bases_node:
            bases = [
                node_text(part)
                for part in iter_children(bases_node)
                if part.type not in (",", "(", ")")
            ]

        docstring_range = extract_docstring_range(node)
        
        cls_id = generate_id()
        cls_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        body_node = node.child_by_field_name("body")
        methods = self._extract_functions(body_node, context, type="METHOD", parent_id=cls_id, parent_fqn=cls_fqn) if body_node else []
        inner_classes = self._traverse_block_for_classes(body_node, context, parent_id=cls_id, parent_fqn=cls_fqn) if body_node else []
        class_variables = self._extract_variables(body_node, context, parent_id=cls_id, parent_fqn=cls_fqn) if body_node else []

        cls_obj = PythonClass(
            id=cls_id,
            fqn=cls_fqn,
            parent_id=parent_id,
            name=name,
            source_range=source_range,
            docstring_range=docstring_range,
            annotations=decorator_details,
            inherits=bases,
            method_ids=methods,
            inner_type_ids=inner_classes,
            property_ids=class_variables,
            visibility=visibility_from_name(name),
        )
        context.entity_registry.add(cls_obj)
        return cls_obj.id
    
    def _extract_functions(self, block_node: Node, context: Context, type: str = "FUNCTION", parent_id: SymbolID | None = None, parent_fqn: str | None = None) -> list[SymbolID]:
        function_ids: list[SymbolID] = []
        if not block_node:
            return function_ids

        for child in iter_children(block_node):
            if child.type == "function_definition":
                function_ids.append(self._process_function_node(child, [], context, type, parent_id, parent_fqn))
            elif child.type == "decorated_definition":
                definition = child.child_by_field_name("definition")
                if definition and definition.type == "function_definition":
                    decorator_details = extract_decorator_details(child)
                    function_ids.append(self._process_function_node(definition, decorator_details, context, type, parent_id, parent_fqn))
        return function_ids

    def _process_function_node(
        self,
        node: Node,
        decorator_details: list[Annotation],
        context: Context,
        type: str = "FUNCTION",
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None
    ) -> SymbolID:
        source_range = create_source_range(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)

        docstring_range = extract_docstring_range(node)
        signature = extract_signature(node)

        func_id = generate_id()

        func_fqn = f"{parent_fqn}.{name}" if parent_fqn else name
        
        func_obj = PythonFunctionLike(
            id=func_id,
            fqn=func_fqn,
            parent_id=parent_id,
            name=name,
            type=type,
            source_range=source_range,
            docstring_range=docstring_range,
            signature=signature,
            annotations=decorator_details,
            visibility=visibility_from_name(name),
        )
        context.entity_registry.add(func_obj)
        return func_obj.id
    
    def _extract_variables(self, block_node: Node, context: Context, parent_id: SymbolID | None = None, parent_fqn: str | None = None) -> list[SymbolID]:
        variable_ids: list[SymbolID] = []

        for child in iter_children(block_node):
            if child.type == "expression_statement":
                inner = first_child(child)
                if inner:
                    for v in collect_from_assignment_node(node=inner, parent_fqn=parent_fqn, parent_id=parent_id):
                        context.entity_registry.add(v)
                        variable_ids.append(v.id)
                continue
            for v in collect_from_assignment_node(node=child, parent_fqn=parent_fqn, parent_id=parent_id):
                context.entity_registry.add(v)
                variable_ids.append(v.id)
        
        return variable_ids
    
    def _extract_all_exports(self, root: Node) -> list[str] | None:
        cursor = QueryCursor(self.all_exports_query)
        captures_dict = cursor.captures(root)

        for name, nodes in captures_dict.items():
            for n in nodes:
                if name == "all_values":
                    exports = []
                    for child in iter_children(n):
                        if child.type == "string":
                            export_name = node_text(child).strip().strip('"').strip("'")
                            exports.append(export_name)
                    return exports
        
        return None
    
    def _process_import_statement(
        self, 
        node: Node, 
        context: Context,
        parent_id: SymbolID | None = None
    ) -> SymbolID:
        source_range = create_source_range(node)
        alias_ids = []
        import_stmt_id = generate_id()

        for child in iter_children(node):
            if child.type == "dotted_name":
                child_source_range = create_source_range(child)
                import_alias = PythonImportAlias(
                    name=node_text(child),
                    alias=None,
                    parent_id=import_stmt_id,
                    source_range=child_source_range
                )
                context.entity_registry.add(import_alias)
                alias_ids.append(import_alias.id)
            
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                alias_node = child.child_by_field_name("alias")
                child_source_range = create_source_range(name_node) if name_node else source_range
                if name_node:
                    import_alias = PythonImportAlias(
                        name=node_text(name_node),
                        alias=node_text(alias_node) if alias_node else None,
                        parent_id=import_stmt_id,
                        source_range=child_source_range
                    )
                    context.entity_registry.add(import_alias)
                    alias_ids.append(import_alias.id)

        import_stmt = PythonImportStatement(
            id=import_stmt_id,
            type="generic_import",
            parent_id=parent_id,
            source_range=source_range,
            path="",
            name_ids=alias_ids,
            wildcard=False,
        )
        context.entity_registry.add(import_stmt)
        return import_stmt.id
    
    def _process_import_from_statement(
        self, 
        node: Node, 
        context: Context,
        parent_id: SymbolID | None = None
    ) -> SymbolID:
        source_range = create_source_range(node)
        module_node = node.child_by_field_name("module_name")
        module_name = node_text(module_node) if module_node else ""

        alias_ids: list[SymbolID] = []
        wildcard = False

        import_stmt_id = generate_id()

        for child in iter_children(node):
            if child.type == "wildcard_import":
                wildcard = True
            
            elif child.type == "dotted_name":
                if child != module_node:
                    import_alias = PythonImportAlias(
                        name=node_text(child),
                        alias=None,
                        parent_id=import_stmt_id,
                        source_range=create_source_range(child)
                    )
                    context.entity_registry.add(import_alias)
                    alias_ids.append(import_alias.id)
            
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                alias_node = child.child_by_field_name("alias")
                child_source_range = create_source_range(name_node) if name_node else source_range
                if name_node:
                    import_alias = PythonImportAlias(
                        name=node_text(name_node),
                        alias=node_text(alias_node) if alias_node else None,
                        parent_id=import_stmt_id,
                        source_range=child_source_range
                    )
                    context.entity_registry.add(import_alias)
                    alias_ids.append(import_alias.id)

        import_stmt = PythonImportStatement(
            id=import_stmt_id,
            type="from_import",
            parent_id=parent_id,
            source_range=source_range,
            path=module_name,
            name_ids=alias_ids,
            wildcard=wildcard,
        )
        context.entity_registry.add(import_stmt)
        return import_stmt.id
    
    def _extract_import_statements(
        self, 
        root: Node,
        context: Context,
        parent_id: SymbolID | None = None
    ) -> list[SymbolID]:
        import_stmt_ids: list[SymbolID] = []

        for child in iter_children(root):
            if child.type == "import_statement":
                import_stmt_id = self._process_import_statement(child, context, parent_id)
                import_stmt_ids.append(import_stmt_id)
            
            elif child.type == "import_from_statement":
                import_stmt_id = self._process_import_from_statement(child, context, parent_id)
                import_stmt_ids.append(import_stmt_id)
        
        return import_stmt_ids

    def _extract_control_flow_groups(
        self,
        block_node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None
    ) -> list[SymbolID]:
        group_ids: list[SymbolID] = []

        if not block_node:
            return group_ids
        
        for child in iter_children(block_node):
            if child.type == "if_statement":
                grp_id = generate_id()
                grp = ControlFlowGroup(
                    id=grp_id,
                    parent_id=parent_id,
                    group_type="if_statement",
                    source_range=create_source_range(child),
                    block_ids=self._process_if_node(child, context, parent_id=grp_id, parent_fqn=parent_fqn),
                )
                context.entity_registry.add(grp)
                group_ids.append(grp.id)
            
            elif child.type == "try_statement":
                grp_id = generate_id()
                grp = ControlFlowGroup(
                    id=grp_id,
                    parent_id=parent_id,
                    group_type="try_statement",
                    source_range=create_source_range(child),
                    block_ids=self._process_try_node(child, context, parent_id=grp_id, parent_fqn=parent_fqn),
                )
                context.entity_registry.add(grp)
                group_ids.append(grp.id)
        
        return group_ids

    def _process_if_node(self, node: Node, context: Context, parent_id: SymbolID | None = None, parent_fqn: str | None = None) -> list[SymbolID]:
        result_ids: list[SymbolID] = []
        source_range = create_source_range(node)

        condition_node = node.child_by_field_name("condition")
        condition_range = create_source_range(condition_node) if condition_node else None
        
        consequence_node = node.child_by_field_name("consequence")
        if consequence_node:
            blk_id = generate_id()
            blk = ControlFlowBlock(
                id=blk_id,
                parent_id=parent_id,
                branch="if",
                source_range=source_range,
                condition_range=condition_range,
                import_stmt_ids=self._extract_import_statements(consequence_node, context, parent_id=blk_id),
                type_ids=self._traverse_block_for_classes(consequence_node, context, parent_id=blk_id, parent_fqn=parent_fqn),
                function_ids=self._extract_functions(consequence_node, context, type="FUNCTION", parent_id=blk_id, parent_fqn=parent_fqn),
                variable_ids=self._extract_variables(consequence_node, context, parent_id=blk_id, parent_fqn=parent_fqn),
                nested_group_ids=self._extract_control_flow_groups(consequence_node, context, parent_id=blk_id, parent_fqn=parent_fqn),
            )
            context.entity_registry.add(blk)
            result_ids.append(blk.id)
            
        for child in iter_children(node):
            if child.type == "elif_clause":
                alt_cond_node = child.child_by_field_name("condition")
                alt_cond_range = create_source_range(alt_cond_node) if alt_cond_node else None
                alt_body = child.child_by_field_name("consequence")
                if alt_body:
                    blk_id = generate_id()
                    blk = ControlFlowBlock(
                        id=blk_id,
                        parent_id=parent_id,
                        branch="elif",
                        source_range=create_source_range(child),
                        condition_range=alt_cond_range,
                        import_stmt_ids=self._extract_import_statements(alt_body, context, parent_id=blk_id),
                        type_ids=self._traverse_block_for_classes(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        function_ids=self._extract_functions(alt_body, context, type="FUNCTION", parent_id=blk_id, parent_fqn=parent_fqn),
                        variable_ids=self._extract_variables(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        nested_group_ids=self._extract_control_flow_groups(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                    )
                    context.entity_registry.add(blk)
                    result_ids.append(blk.id)
            
            elif child.type == "else_clause":
                alt_body = child.child_by_field_name("body")
                if alt_body:
                    blk_id = generate_id()
                    blk = ControlFlowBlock(
                        id=blk_id,
                        parent_id=parent_id,
                        branch="else",
                        source_range=create_source_range(child),
                        condition_range=None,
                        import_stmt_ids=self._extract_import_statements(alt_body, context, parent_id=blk_id),
                        type_ids=self._traverse_block_for_classes(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        function_ids=self._extract_functions(alt_body, context, type="FUNCTION", parent_id=blk_id, parent_fqn=parent_fqn),
                        variable_ids=self._extract_variables(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        nested_group_ids=self._extract_control_flow_groups(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                    )
                    context.entity_registry.add(blk)
                    result_ids.append(blk.id)
        
        return result_ids

    def _process_try_node(self, node: Node, context: Context, parent_id: SymbolID | None = None, parent_fqn: str | None = None) -> list[SymbolID]:
        result_ids: list[SymbolID] = []
        source_range = create_source_range(node)
        body_node = node.child_by_field_name("body")
        if body_node:
            blk_id = generate_id()
            blk = ControlFlowBlock(
                id=blk_id,
                parent_id=parent_id,
                branch="try",
                source_range=source_range,
                condition_range=None,
                import_stmt_ids=self._extract_import_statements(body_node, context, parent_id=blk_id),
                type_ids=self._traverse_block_for_classes(body_node, context, parent_id=blk_id, parent_fqn=parent_fqn),
                function_ids=self._extract_functions(body_node, context, type="FUNCTION", parent_id=blk_id, parent_fqn=parent_fqn),
                variable_ids=self._extract_variables(body_node, context, parent_id=blk_id, parent_fqn=parent_fqn),
                nested_group_ids=self._extract_control_flow_groups(body_node, context, parent_id=blk_id, parent_fqn=parent_fqn),
            )
            context.entity_registry.add(blk)
            result_ids.append(blk.id)
            
        for child in iter_children(node):
            if child.type in ("except_clause", "except_group_clause"):
                body = child.child_by_field_name("body")
                if body:
                    condition_range = create_source_range(child.child_by_field_name("condition")) if child.child_by_field_name("condition") else None
                    blk_id = generate_id()
                    blk = ControlFlowBlock(
                        id=blk_id,
                        parent_id=parent_id,
                        branch="except",
                        source_range=create_source_range(child),
                        condition_range=condition_range,
                        import_stmt_ids=self._extract_import_statements(body, context, parent_id=blk_id),
                        type_ids=self._traverse_block_for_classes(body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        function_ids=self._extract_functions(body, context, type="FUNCTION", parent_id=blk_id, parent_fqn=parent_fqn),
                        variable_ids=self._extract_variables(body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        nested_group_ids=self._extract_control_flow_groups(body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                    )
                    context.entity_registry.add(blk)
                    result_ids.append(blk.id)
            
            elif child.type == "else_clause":
                alt_body = child.child_by_field_name("body")
                if alt_body:
                    blk_id = generate_id()
                    blk = ControlFlowBlock(
                        id=blk_id,
                        parent_id=parent_id,
                        branch="else",
                        source_range=create_source_range(child),
                        condition_range=None,
                        import_stmt_ids=self._extract_import_statements(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        type_ids=self._traverse_block_for_classes(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        function_ids=self._extract_functions(alt_body, context, type="FUNCTION", parent_id=blk_id, parent_fqn=parent_fqn),
                        variable_ids=self._extract_variables(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        nested_group_ids=self._extract_control_flow_groups(alt_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                    )
                    context.entity_registry.add(blk)
                    result_ids.append(blk.id)
            
            elif child.type == "finally_clause":
                fin_body = None
                for cc in iter_children(child):
                    if cc.type == "block":
                        fin_body = cc
                if fin_body:
                    blk_id = generate_id()
                    blk = ControlFlowBlock(
                        id=blk_id,
                        parent_id=parent_id,
                        branch="finally",
                        source_range=create_source_range(child),
                        condition_range=None,
                        import_stmt_ids=self._extract_import_statements(fin_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        type_ids=self._traverse_block_for_classes(fin_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        function_ids=self._extract_functions(fin_body, context, type="FUNCTION", parent_id=blk_id, parent_fqn=parent_fqn),
                        variable_ids=self._extract_variables(fin_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                        nested_group_ids=self._extract_control_flow_groups(fin_body, context, parent_id=blk_id, parent_fqn=parent_fqn),
                    )
                    context.entity_registry.add(blk)
                    result_ids.append(blk.id)
        
        return result_ids
