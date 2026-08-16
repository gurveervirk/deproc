import os
from typing import ClassVar

from deproc.core.context import Context
from deproc.core.interfaces import SourceParser
from deproc.utils.tree_walk import iter_children
from tree_sitter import Node

from .models import (
    Annotation,
    JavaAnnotationType,
    JavaClass,
    JavaCompilationUnit,
    JavaEnum,
    JavaEnumConstant,
    JavaField,
    JavaImport,
    JavaInterface,
    JavaMethod,
    JavaRecord,
    JavaRecordComponent,
    SimpleBinding,
    SourceRange,
    SymbolID,
)
from .utils.extraction import (
    extract_annotations,
    extract_exceptions,
    extract_javadoc_range,
    extract_signature,
    extract_type_names,
)
from .utils.misc import (
    extract_modifier_names,
    visibility_from_modifiers,
)
from .utils.tree_sitter_java import (
    create_source_range,
    get_java_language,
    get_java_parser,
    node_text,
)


class JavaSourceParser(SourceParser):
    def __init__(self):
        self._parser = get_java_parser()
        self._language = get_java_language()
        self._current_source_file_id: str | None = None

    def _sr(self, node: Node) -> SourceRange:
        return create_source_range(node, source_id=self._current_source_file_id)

    def _modifiers_node(self, node: Node) -> Node | None:
        for child in iter_children(node):
            if child.type == "modifiers":
                return child
        return None

    def _child_by_type(self, node: Node, node_type: str) -> Node | None:
        for child in iter_children(node):
            if child.type == node_type:
                return child
        return None

    def _modifier_names(self, node: Node) -> list[str]:
        return extract_modifier_names(self._modifiers_node(node))

    def _annotations(self, node: Node) -> list[Annotation]:
        return extract_annotations(
            self._modifiers_node(node), source_file_id=self._current_source_file_id
        )

    def _compute_fqn(
        self, file_path: str, context: Context, package_fqn: str | None
    ) -> str:
        if package_fqn:
            file_stem = os.path.splitext(os.path.basename(file_path))[0]
            return f"{package_fqn}.{file_stem}"
        relative_path = os.path.relpath(file_path, context.base_path)
        without_extension = os.path.splitext(relative_path)[0]
        return without_extension.replace(os.sep, ".")

    def parse_file(self, path: str, context: Context) -> JavaCompilationUnit:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        if not path.endswith(".java"):
            raise ValueError(f"Unsupported file extension for Java parser: {path}")

        with open(path, "rb") as f:
            source_bytes = f.read()
        tree = self._parser.parse(source_bytes)
        root_node = tree.root_node

        package_fqn = self._extract_package(root_node)
        cu_fqn = self._compute_fqn(path, context, package_fqn)

        relative_path = os.path.relpath(path, context.base_path).replace("\\", "/")

        source_file = JavaCompilationUnit(
            fqn=cu_fqn,
            package_fqn=package_fqn,
            path=relative_path,
            source=source_bytes.decode("utf-8"),
            docstring_range=None,
        )

        self._current_source_file_id = source_file.id
        source_file.docstring_range = self._extract_file_docstring(root_node)
        source_file.import_stmt_ids = self._extract_imports(
            root_node, context, parent_id=source_file.id
        )
        source_file.type_ids = self._extract_types(
            root_node, context, parent_id=source_file.id, parent_fqn=package_fqn
        )

        context.entity_registry.add(source_file)
        return source_file

    def _extract_file_docstring(self, root: Node) -> SourceRange | None:
        for child in iter_children(root):
            if child.type in ("block_comment", "comment"):
                text = node_text(child)
                if text.startswith("/**"):
                    return create_source_range(
                        child, source_id=self._current_source_file_id
                    )
            elif child.type not in ("package_declaration", "import_declaration"):
                break
        return None

    def _extract_package(self, root: Node) -> str | None:
        for child in iter_children(root):
            if child.type == "package_declaration":
                scoped = child.child_by_field_name("name")
                if scoped is not None:
                    return node_text(scoped)
                for sub in iter_children(child):
                    if sub.type == "scoped_identifier":
                        return node_text(sub)
        return None

    def _extract_imports(
        self, root: Node, context: Context, parent_id: SymbolID | None = None
    ) -> list[SymbolID]:
        import_ids: list[SymbolID] = []
        for child in iter_children(root):
            if child.type == "import_declaration":
                import_obj = self._process_import(child, context, parent_id)
                if import_obj is not None:
                    import_ids.append(import_obj.id)
        return import_ids

    def _process_import(
        self, node: Node, context: Context, parent_id: SymbolID | None = None
    ) -> JavaImport | None:
        source_range = self._sr(node)

        is_static = False
        is_wildcard = False
        scoped = None
        for child in iter_children(node):
            if child.type == "static":
                is_static = True
            elif child.type == "scoped_identifier":
                scoped = child
            elif child.type == "asterisk":
                is_wildcard = True

        if scoped is None:
            return None

        import_path = node_text(scoped)
        if is_wildcard:
            import_path = f"{import_path}.*"

        if is_static:
            import_kind = "static_on_demand" if is_wildcard else "single_static"
        else:
            import_kind = "on_demand" if is_wildcard else "single_type"

        imported_name = None
        if import_kind in ("single_type", "single_static"):
            imported_name = import_path.rsplit(".", 1)[-1]

        import_obj = JavaImport(
            parent_id=parent_id,
            import_path=import_path,
            import_kind=import_kind,
            imported_name=imported_name,
            source_range=source_range,
        )
        context.entity_registry.add(import_obj)
        return import_obj

    def _extract_types(
        self,
        root: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        type_ids: list[SymbolID] = []
        for child in iter_children(root):
            if child.type == "class_declaration":
                type_ids.append(
                    self._process_class(child, context, parent_id, parent_fqn)
                )
            elif child.type == "interface_declaration":
                type_ids.append(
                    self._process_interface(child, context, parent_id, parent_fqn)
                )
            elif child.type == "enum_declaration":
                type_ids.append(
                    self._process_enum(child, context, parent_id, parent_fqn)
                )
            elif child.type == "record_declaration":
                type_ids.append(
                    self._process_record(child, context, parent_id, parent_fqn)
                )
            elif child.type == "annotation_type_declaration":
                type_ids.append(
                    self._process_annotation_type(child, context, parent_id, parent_fqn)
                )
        return type_ids

    def _process_class(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> SymbolID:
        source_range = self._sr(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)
        modifier_names = self._modifier_names(node)
        annotations = self._annotations(node)
        docstring_range = extract_javadoc_range(
            node, source_file_id=self._current_source_file_id
        )

        type_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        superclass = None
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node is not None:
            names = extract_type_names(superclass_node)
            superclass = names[0] if names else None

        implements = []
        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node is not None:
            implements = extract_type_names(interfaces_node)

        body_node = node.child_by_field_name("body")

        cls_obj = JavaClass(
            name=name,
            fqn=type_fqn,
            parent_id=parent_id,
            source_range=source_range,
            docstring_range=docstring_range,
            annotations=annotations,
            visibility=visibility_from_modifiers(modifier_names),
            is_abstract="abstract" in modifier_names,
            is_final="final" in modifier_names,
            is_static="static" in modifier_names,
            superclass=superclass,
            implements=implements,
        )

        cls_obj.method_ids = (
            self._extract_methods(
                body_node, context, parent_id=cls_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        cls_obj.method_ids += (
            self._extract_constructors(
                body_node, context, parent_id=cls_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        cls_obj.property_ids = (
            self._extract_fields(
                body_node, context, parent_id=cls_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        cls_obj.inner_type_ids = (
            self._extract_inner_types(
                body_node, context, parent_id=cls_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        context.entity_registry.add(cls_obj)
        return cls_obj.id

    def _process_interface(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> SymbolID:
        source_range = self._sr(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)
        modifier_names = self._modifier_names(node)
        annotations = self._annotations(node)
        docstring_range = extract_javadoc_range(
            node, source_file_id=self._current_source_file_id
        )

        type_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        extends = []
        extends_node = node.child_by_field_name(
            "extends_interfaces"
        ) or self._child_by_type(node, "extends_interfaces")
        if extends_node is not None:
            extends = extract_type_names(extends_node)

        body_node = node.child_by_field_name("body")

        iface_obj = JavaInterface(
            name=name,
            fqn=type_fqn,
            parent_id=parent_id,
            source_range=source_range,
            docstring_range=docstring_range,
            annotations=annotations,
            visibility=visibility_from_modifiers(modifier_names),
            extends_interfaces=extends,
        )

        iface_obj.method_ids = (
            self._extract_methods(
                body_node, context, parent_id=iface_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        iface_obj.property_ids = (
            self._extract_fields(
                body_node, context, parent_id=iface_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        iface_obj.inner_type_ids = (
            self._extract_inner_types(
                body_node, context, parent_id=iface_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        context.entity_registry.add(iface_obj)
        return iface_obj.id

    def _process_enum(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> SymbolID:
        source_range = self._sr(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)
        modifier_names = self._modifier_names(node)
        annotations = self._annotations(node)
        docstring_range = extract_javadoc_range(
            node, source_file_id=self._current_source_file_id
        )

        type_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        implements = []
        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node is not None:
            implements = extract_type_names(interfaces_node)

        body_node = node.child_by_field_name("body")

        declarations_node = (
            self._child_by_type(body_node, "enum_body_declarations")
            if body_node
            else None
        )
        member_node = declarations_node if declarations_node is not None else body_node

        enum_obj = JavaEnum(
            name=name,
            fqn=type_fqn,
            parent_id=parent_id,
            source_range=source_range,
            docstring_range=docstring_range,
            annotations=annotations,
            visibility=visibility_from_modifiers(modifier_names),
            implements=implements,
        )

        enum_obj.enum_constant_ids = (
            self._extract_enum_constants(
                body_node, context, parent_id=enum_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        enum_obj.method_ids = (
            self._extract_methods(
                member_node, context, parent_id=enum_obj.id, parent_fqn=type_fqn
            )
            if member_node
            else []
        )
        enum_obj.method_ids += (
            self._extract_constructors(
                member_node, context, parent_id=enum_obj.id, parent_fqn=type_fqn
            )
            if member_node
            else []
        )
        enum_obj.property_ids = (
            self._extract_fields(
                member_node, context, parent_id=enum_obj.id, parent_fqn=type_fqn
            )
            if member_node
            else []
        )
        enum_obj.inner_type_ids = (
            self._extract_inner_types(
                member_node, context, parent_id=enum_obj.id, parent_fqn=type_fqn
            )
            if member_node
            else []
        )
        context.entity_registry.add(enum_obj)
        return enum_obj.id

    def _process_record(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> SymbolID:
        source_range = self._sr(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)
        modifier_names = self._modifier_names(node)
        annotations = self._annotations(node)
        docstring_range = extract_javadoc_range(
            node, source_file_id=self._current_source_file_id
        )

        type_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        implements = []
        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node is not None:
            implements = extract_type_names(interfaces_node)

        body_node = node.child_by_field_name("body")

        record_obj = JavaRecord(
            name=name,
            fqn=type_fqn,
            parent_id=parent_id,
            source_range=source_range,
            docstring_range=docstring_range,
            annotations=annotations,
            visibility=visibility_from_modifiers(modifier_names),
            implements=implements,
        )

        record_obj.record_component_ids = self._extract_record_components(
            node, context, parent_id=record_obj.id, parent_fqn=type_fqn
        )
        record_obj.method_ids = (
            self._extract_methods(
                body_node, context, parent_id=record_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        record_obj.method_ids += (
            self._extract_constructors(
                body_node, context, parent_id=record_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        record_obj.property_ids = (
            self._extract_fields(
                body_node, context, parent_id=record_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        record_obj.inner_type_ids = (
            self._extract_inner_types(
                body_node, context, parent_id=record_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        context.entity_registry.add(record_obj)
        return record_obj.id

    def _process_annotation_type(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> SymbolID:
        source_range = self._sr(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)
        modifier_names = self._modifier_names(node)
        annotations = self._annotations(node)
        docstring_range = extract_javadoc_range(
            node, source_file_id=self._current_source_file_id
        )

        type_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        body_node = node.child_by_field_name("body")

        anno_obj = JavaAnnotationType(
            name=name,
            fqn=type_fqn,
            parent_id=parent_id,
            source_range=source_range,
            docstring_range=docstring_range,
            annotations=annotations,
            visibility=visibility_from_modifiers(modifier_names),
        )

        anno_obj.method_ids = (
            self._extract_methods(
                body_node, context, parent_id=anno_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        anno_obj.inner_type_ids = (
            self._extract_inner_types(
                body_node, context, parent_id=anno_obj.id, parent_fqn=type_fqn
            )
            if body_node
            else []
        )
        context.entity_registry.add(anno_obj)
        return anno_obj.id

    _TYPE_DECLARATION_NODES: ClassVar[dict[str, str]] = {
        "class_declaration": "_process_class",
        "interface_declaration": "_process_interface",
        "enum_declaration": "_process_enum",
        "record_declaration": "_process_record",
        "annotation_type_declaration": "_process_annotation_type",
    }

    def _extract_inner_types(
        self,
        block_node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        inner_ids: list[SymbolID] = []
        if not block_node:
            return inner_ids

        anon_counter = 0
        for child in iter_children(block_node):
            handler_name = self._TYPE_DECLARATION_NODES.get(child.type)
            if handler_name is not None:
                handler = getattr(self, handler_name)
                inner_ids.append(handler(child, context, parent_id, parent_fqn))
                continue
            if child.type == "field_declaration":
                for oce in self._find_anonymous_class_nodes(child):
                    anon_counter += 1
                    inner_ids.append(
                        self._process_anonymous_class(
                            oce, context, parent_id, parent_fqn, anon_counter
                        )
                    )
        return inner_ids

    def _find_anonymous_class_nodes(self, node: Node) -> list[Node]:
        found: list[Node] = []
        for child in iter_children(node):
            if child.type in (
                "class_body",
                "method_declaration",
                "constructor_declaration",
                "block",
            ):
                continue
            if (
                child.type == "object_creation_expression"
                and self._child_by_type(child, "class_body") is not None
            ):
                found.append(child)
                continue
            found.extend(self._find_anonymous_class_nodes(child))
        return found

    def _process_anonymous_class(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
        ordinal: int = 1,
    ) -> SymbolID:
        source_range = self._sr(node)

        name = None
        parent = node.parent
        if parent is not None:
            declarator_name = parent.child_by_field_name("name")
            if declarator_name is not None:
                name = node_text(declarator_name)
        if not name:
            name = f"${ordinal}"

        anon_fqn = f"{parent_fqn}${ordinal}" if parent_fqn else f"${ordinal}"

        body_node = self._child_by_type(node, "class_body")

        anon_obj = JavaClass(
            name=name,
            fqn=anon_fqn,
            parent_id=parent_id,
            source_range=source_range,
            docstring_range=None,
            visibility="package-private",
        )

        anon_obj.method_ids = (
            self._extract_methods(
                body_node, context, parent_id=anon_obj.id, parent_fqn=anon_fqn
            )
            if body_node
            else []
        )
        anon_obj.property_ids = (
            self._extract_fields(
                body_node, context, parent_id=anon_obj.id, parent_fqn=anon_fqn
            )
            if body_node
            else []
        )
        context.entity_registry.add(anon_obj)
        return anon_obj.id

    def _extract_methods(
        self,
        block_node: Node,
        context: Context,
        type: str = "METHOD",
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        method_ids: list[SymbolID] = []
        if not block_node:
            return method_ids

        for child in iter_children(block_node):
            if child.type == "method_declaration":
                method_ids.append(
                    self._process_method(child, context, type, parent_id, parent_fqn)
                )
        return method_ids

    def _process_method(
        self,
        node: Node,
        context: Context,
        type: str = "METHOD",
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> SymbolID:
        source_range = self._sr(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)
        modifier_names = self._modifier_names(node)
        annotations = self._annotations(node)
        docstring_range = extract_javadoc_range(
            node, source_file_id=self._current_source_file_id
        )
        signature = extract_signature(node, source_file_id=self._current_source_file_id)

        func_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        func_obj = JavaMethod(
            name=name,
            fqn=func_fqn,
            parent_id=parent_id,
            type=type,
            source_range=source_range,
            docstring_range=docstring_range,
            signature=signature,
            exceptions=extract_exceptions(node),
            is_abstract="abstract" in modifier_names,
            is_final="final" in modifier_names,
            is_static="static" in modifier_names,
            is_default="default" in modifier_names,
            is_synchronized="synchronized" in modifier_names,
            is_native="native" in modifier_names,
            visibility=visibility_from_modifiers(modifier_names),
            annotations=annotations,
        )
        context.entity_registry.add(func_obj)
        return func_obj.id

    def _extract_constructors(
        self,
        block_node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        constructor_ids: list[SymbolID] = []
        if not block_node:
            return constructor_ids

        for child in iter_children(block_node):
            if child.type == "constructor_declaration":
                constructor_ids.append(
                    self._process_constructor(child, context, parent_id, parent_fqn)
                )
        return constructor_ids

    def _process_constructor(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> SymbolID:
        source_range = self._sr(node)
        name_node = node.child_by_field_name("name")
        name = node_text(name_node)
        modifier_names = self._modifier_names(node)
        annotations = self._annotations(node)
        docstring_range = extract_javadoc_range(
            node, source_file_id=self._current_source_file_id
        )
        signature = extract_signature(node, source_file_id=self._current_source_file_id)

        func_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

        func_obj = JavaMethod(
            name=name,
            fqn=func_fqn,
            parent_id=parent_id,
            type="CONSTRUCTOR",
            source_range=source_range,
            docstring_range=docstring_range,
            signature=signature,
            exceptions=extract_exceptions(node),
            is_abstract=False,
            is_final="final" in modifier_names,
            is_static=False,
            is_default=False,
            is_synchronized="synchronized" in modifier_names,
            is_native=False,
            visibility=visibility_from_modifiers(modifier_names),
            annotations=annotations,
        )
        context.entity_registry.add(func_obj)
        return func_obj.id

    def _extract_fields(
        self,
        block_node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        field_ids: list[SymbolID] = []
        if not block_node:
            return field_ids

        for child in iter_children(block_node):
            if child.type == "field_declaration":
                field_ids.extend(
                    self._process_field_declaration(
                        child, context, parent_id, parent_fqn
                    )
                )
        return field_ids

    def _process_field_declaration(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        field_ids: list[SymbolID] = []
        source_range = self._sr(node)
        modifier_names = self._modifier_names(node)
        type_node = node.child_by_field_name("type")
        type_annotation = (
            create_source_range(type_node, source_id=self._current_source_file_id)
            if type_node is not None
            else None
        )

        for child in iter_children(node):
            if child.type != "variable_declarator":
                continue
            name_node = child.child_by_field_name("name")
            name = node_text(name_node)
            field_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

            field_obj = JavaField(
                type="FIELD",
                parent_id=parent_id,
                source_range=source_range,
                variable_binding=SimpleBinding(name=name, fqn=field_fqn),
                value_range=None,
                type_annotation=type_annotation,
                modifiers=modifier_names,
                is_static="static" in modifier_names,
                is_final="final" in modifier_names,
                is_transient="transient" in modifier_names,
                is_volatile="volatile" in modifier_names,
            )
            context.entity_registry.add(field_obj)
            field_ids.append(field_obj.id)
        return field_ids

    def _extract_enum_constants(
        self,
        block_node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        constant_ids: list[SymbolID] = []
        if not block_node:
            return constant_ids

        for child in iter_children(block_node):
            if child.type != "enum_constant":
                continue
            name_node = child.child_by_field_name("name")
            name = node_text(name_node)
            constant_fqn = f"{parent_fqn}.{name}" if parent_fqn else name
            arguments_node = self._child_by_type(child, "argument_list")

            constant_obj = JavaEnumConstant(
                parent_id=parent_id,
                name=name,
                fqn=constant_fqn,
                source_range=self._sr(child),
                arguments_range=create_source_range(
                    arguments_node, source_id=self._current_source_file_id
                )
                if arguments_node is not None
                else None,
            )
            context.entity_registry.add(constant_obj)
            constant_ids.append(constant_obj.id)
        return constant_ids

    def _extract_record_components(
        self,
        node: Node,
        context: Context,
        parent_id: SymbolID | None = None,
        parent_fqn: str | None = None,
    ) -> list[SymbolID]:
        component_ids: list[SymbolID] = []
        params_node = node.child_by_field_name("parameters")
        if params_node is None:
            return component_ids

        for child in iter_children(params_node):
            if child.type != "formal_parameter":
                continue
            name_node = child.child_by_field_name("name")
            name = node_text(name_node)
            type_node = child.child_by_field_name("type")
            component_fqn = f"{parent_fqn}.{name}" if parent_fqn else name

            component_obj = JavaRecordComponent(
                parent_id=parent_id,
                name=name,
                fqn=component_fqn,
                source_range=self._sr(child),
                type_annotation=create_source_range(
                    type_node, source_id=self._current_source_file_id
                )
                if type_node is not None
                else None,
            )
            context.entity_registry.add(component_obj)
            component_ids.append(component_obj.id)
        return component_ids
