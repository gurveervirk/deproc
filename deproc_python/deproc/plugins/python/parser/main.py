from deproc.core.interfaces import SourceParser
from deproc.core.context import Context
from deproc.utils import iter_children, first_child
from tree_sitter import Query, Node, QueryCursor
import os

from .models import (
    Annotation,
    PythonClass,
    ControlFlowBlock,
    ControlFlowGroup,
    PythonFunctionLike,
    PythonImportStatement,
    PythonImportAlias,
    PythonSourceFile,
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

        self.import_query = Query(
            self._language,
            """
            (import_statement) @import
            (import_from_statement) @import_from
            """,
        )
        self.all_exports_query = Query(
            self._language,
            """
            (expression_statement
                (assignment
                    left: (identifier) @all_name (#eq? @all_name "__all__")
                    right: [(list) (tuple)] @all_values
                )"""
        )

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
        
        source_file.type_ids = self._extract_classes(root_node, source_bytes, context, parent_id=source_file.id)
        source_file.function_ids = self._extract_functions(root_node, source_bytes, context, type="FUNCTION", parent_id=source_file.id)
        source_file.variable_ids = self._extract_variables(root_node, source_bytes, context, parent_id=source_file.id)
        source_file.import_statements = self._extract_import_statements(root_node)
        source_file.all_exports = self._extract_all_exports(root_node)
        source_file.control_flow_group_ids = self._extract_control_flow_groups(root_node, source_bytes, context, parent_id=source_file.id)

        context.entity_registry.add(source_file)
        return source_file
    
    def _extract_classes(self, root: Node, source: bytes, context: Context, parent_id: str | None = None) -> list[str]:
        return self._traverse_block_for_classes(root, source, context, parent_id)
    
    def _traverse_block_for_classes(self, block_node: Node, source: bytes, context: Context, parent_id: str | None = None) -> list[str]:
        class_ids = []

        for child in iter_children(block_node):
            if child.type == "class_definition":
                class_ids.append(self._process_class_node(child, source, [], context, parent_id))
            elif child.type == "decorated_definition":
                definition = child.child_by_field_name("definition")
                if definition and definition.type == "class_definition":
                    decorator_details = extract_decorator_details(child, source)
                    class_ids.append(self._process_class_node(definition, source, decorator_details, context, parent_id))

        return class_ids
    
    def _process_class_node(
        self,
        node: Node,
        source: bytes,
        decorator_details: list[Annotation],
        context: Context,
        parent_id: str | None = None,
    ) -> str:
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

        body_node = node.child_by_field_name("body")
        methods = self._extract_functions(body_node, source, context, type="METHOD", parent_id=cls_id) if body_node else []
        inner_classes = self._traverse_block_for_classes(body_node, source, context, parent_id=cls_id) if body_node else []
        class_variables = self._extract_variables(body_node, source, context, parent_id=cls_id) if body_node else []

        cls_obj = PythonClass(
            id=cls_id,
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
    
    def _extract_functions(self, block_node: Node, source: bytes, context: Context, type: str = "FUNCTION", parent_id: str | None = None) -> list[str]:
        function_ids = []
        if not block_node:
            return function_ids

        for child in iter_children(block_node):
            if child.type == "function_definition":
                function_ids.append(self._process_function_node(child, source, [], context, type, parent_id))
            elif child.type == "decorated_definition":
                definition = child.child_by_field_name("definition")
                if definition and definition.type == "function_definition":
                    decorator_details = extract_decorator_details(child, source)
                    function_ids.append(self._process_function_node(definition, source, decorator_details, context, type, parent_id))
        return function_ids

    def _process_function_node(
        self,
        node: Node,
        source: bytes,
        decorator_details: list[Annotation],
        context: Context,
        type: str = "FUNCTION",
        parent_id: str | None = None,
    ) -> str:
        source_range = create_source_range(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)

        docstring_range = extract_docstring_range(node)
        signature = extract_signature(node)

        func_id = generate_id()
        
        func_obj = PythonFunctionLike(
            id=func_id,
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
    
    def _extract_variables(self, block_node: Node, source: bytes, context: Context, parent_id: str | None = None) -> list[str]:
        variable_ids = []

        for child in iter_children(block_node):
            if child.type == "expression_statement":
                inner = first_child(child)
                if inner:
                    for v in collect_from_assignment_node(inner, source):
                        v.parent_id = parent_id
                        context.entity_registry.add(v)
                        variable_ids.append(v.id)
                continue
            for v in collect_from_assignment_node(child, source):
                v.parent_id = parent_id
                context.entity_registry.add(v)
                variable_ids.append(v.id)
        
        return variable_ids
    
    def _extract_all_exports(self, root: Node) -> list[str] | None:
        cursor = QueryCursor(self.all_exports_query)
        captures_dict = cursor.captures(root)

        for node, name in captures_dict.items():
            for n in node:
                if name == "all_values":
                    exports = []
                    for child in iter_children(n):
                        if child.type == "string":
                            export_name = node_text(child).strip().strip('"').strip("'")
                            exports.append(export_name)
                    return exports
        
        return None
    
    def _extract_import_statements(self, root: Node) -> list[PythonImportStatement]:
        imports = []
        cursor = QueryCursor(self.import_query)
        captures_dict = cursor.captures(root)
        captures = sorted(
            [(n, name) for name, nodes in captures_dict.items() for n in nodes],
            key=lambda x: x[0].start_byte,
        )

        for node, name in captures:
            n = node
            source_range = create_source_range(n)
            
            if name == "import":
                aliases = []
                for child in n.children:
                    if child.type == "dotted_name":
                        aliases.append(PythonImportAlias(name=node_text(child), alias=None))
                    elif child.type == "aliased_import":
                        child_name = child.child_by_field_name("name")
                        child_alias = child.child_by_field_name("alias")
                        if child_name:
                            aliases.append(PythonImportAlias(
                                name=node_text(child_name),
                                alias=node_text(child_alias) if child_alias else None
                            ))
                imports.append(PythonImportStatement(
                    source_range=source_range,
                    type="import",
                    path="",
                    names=aliases
                ))
            elif name == "import_from":
                module_node = n.child_by_field_name("module_name")
                module_name = node_text(module_node)
                aliases = []
                wildcard = False
                for child in n.children:
                    if child.type == "wildcard_import":
                        wildcard = True
                    elif child.type == "dotted_name":
                        if child != module_node:
                            aliases.append(PythonImportAlias(name=node_text(child), alias=None))
                    elif child.type == "aliased_import":
                        child_name = child.child_by_field_name("name")
                        child_alias = child.child_by_field_name("alias")
                        if child_name:
                            aliases.append(PythonImportAlias(
                                name=node_text(child_name),
                                alias=node_text(child_alias) if child_alias else None
                            ))
                imports.append(PythonImportStatement(
                    source_range=source_range,
                    type="import_from",
                    path=module_name,
                    names=aliases,
                    wildcard=wildcard
                ))
        return imports
    
    def _extract_control_flow_groups(
        self,
        block_node: Node,
        source: bytes,
        context: Context,
        parent_id: str | None = None,
    ) -> list[str]:
        group_ids = []

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
                    block_ids=self._process_if_node(child, source, context, parent_id=grp_id),
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
                    block_ids=self._process_try_node(child, source, context, parent_id=grp_id),
                )
                context.entity_registry.add(grp)
                group_ids.append(grp.id)
        
        return group_ids

    def _process_if_node(self, node: Node, source: bytes, context: Context, parent_id: str | None = None) -> list[str]:
        result_ids = []
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
                import_statements=self._extract_import_statements(consequence_node),
                type_ids=self._traverse_block_for_classes(consequence_node, source, context, parent_id=blk_id),
                function_ids=self._extract_functions(consequence_node, source, context, type="FUNCTION", parent_id=blk_id),
                variable_ids=self._extract_variables(consequence_node, source, context, parent_id=blk_id),
                nested_group_ids=self._extract_control_flow_groups(consequence_node, source, context, parent_id=blk_id),
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
                        import_statements=self._extract_import_statements(alt_body),
                        type_ids=self._traverse_block_for_classes(alt_body, source, context, parent_id=blk_id),
                        function_ids=self._extract_functions(alt_body, source, context, type="FUNCTION", parent_id=blk_id),
                        variable_ids=self._extract_variables(alt_body, source, context, parent_id=blk_id),
                        nested_group_ids=self._extract_control_flow_groups(alt_body, source, context, parent_id=blk_id),
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
                        import_statements=self._extract_import_statements(alt_body),
                        type_ids=self._traverse_block_for_classes(alt_body, source, context, parent_id=blk_id),
                        function_ids=self._extract_functions(alt_body, source, context, type="FUNCTION", parent_id=blk_id),
                        variable_ids=self._extract_variables(alt_body, source, context, parent_id=blk_id),
                        nested_group_ids=self._extract_control_flow_groups(alt_body, source, context, parent_id=blk_id),
                    )
                    context.entity_registry.add(blk)
                    result_ids.append(blk.id)
        
        return result_ids

    def _process_try_node(self, node: Node, source: bytes, context: Context, parent_id: str | None = None) -> list[str]:
        result_ids = []
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
                import_statements=self._extract_import_statements(body_node),
                type_ids=self._traverse_block_for_classes(body_node, source, context, parent_id=blk_id),
                function_ids=self._extract_functions(body_node, source, context, type="FUNCTION", parent_id=blk_id),
                variable_ids=self._extract_variables(body_node, source, context, parent_id=blk_id),
                nested_group_ids=self._extract_control_flow_groups(body_node, source, context, parent_id=blk_id),
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
                        import_statements=self._extract_import_statements(body),
                        type_ids=self._traverse_block_for_classes(body, source, context, parent_id=blk_id),
                        function_ids=self._extract_functions(body, source, context, type="FUNCTION", parent_id=blk_id),
                        variable_ids=self._extract_variables(body, source, context, parent_id=blk_id),
                        nested_group_ids=self._extract_control_flow_groups(body, source, context, parent_id=blk_id),
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
                        import_statements=self._extract_import_statements(alt_body),
                        type_ids=self._traverse_block_for_classes(alt_body, source, context, parent_id=blk_id),
                        function_ids=self._extract_functions(alt_body, source, context, type="FUNCTION", parent_id=blk_id),
                        variable_ids=self._extract_variables(alt_body, source, context, parent_id=blk_id),
                        nested_group_ids=self._extract_control_flow_groups(alt_body, source, context, parent_id=blk_id),
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
                        import_statements=self._extract_import_statements(fin_body),
                        type_ids=self._traverse_block_for_classes(fin_body, source, context, parent_id=blk_id),
                        function_ids=self._extract_functions(fin_body, source, context, type="FUNCTION", parent_id=blk_id),
                        variable_ids=self._extract_variables(fin_body, source, context, parent_id=blk_id),
                        nested_group_ids=self._extract_control_flow_groups(fin_body, source, context, parent_id=blk_id),
                    )
                    context.entity_registry.add(blk)
                    result_ids.append(blk.id)
        
        return result_ids
