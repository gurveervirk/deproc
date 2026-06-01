from ..models import (
    Annotation,
    ComplexBinding,
    PythonConstant,
    PythonTypeAlias,
    SimpleBinding,
    Signature,
    SourceRange,
    VariableDeclaration,
)
from .tree_sitter_python import (
    node_text,
    create_source_range
)
from tree_sitter import Node
from deproc.utils import iter_children, first_child

def extract_docstring_range(node: Node) -> SourceRange | None:
    if node.type == "module":
        body = node
    elif node.type in ("class_definition", "function_definition"):
        body = node.child_by_field_name("body")
    else:
        return None

    if not body:
        return None

    for child in iter_children(body):
        if child.type == "expression_statement":
            first_child_node = first_child(child)
            if first_child_node and first_child_node.type == "string":
                return create_source_range(first_child_node)
        elif child.type == "comment":
            continue
        else:
            break
    return None

def extract_decorator_details(decorated_node: Node) -> list[Annotation]:
    decorators: list[Annotation] = []
    for child in iter_children(decorated_node):
        if child.type == "decorator":
            source_range = create_source_range(child)
            decorators.append(
                Annotation(
                    name=node_text(child).strip(),
                    source_range=source_range
                )
            )
    return decorators

def extract_signature(function_node: Node) -> Signature:
    params_node = function_node.child_by_field_name("parameters")
    arguments_range = create_source_range(params_node) if params_node else None

    return_node = function_node.child_by_field_name("return_type")
    return_type_range = create_source_range(return_node) if return_node else None

    # Preferably use colon as end of signature
    colon_node = None
    for child in function_node.children:
        if child.type == ":":
            colon_node = child
            break

    end_point = colon_node.end_point if colon_node else (return_node.end_point if return_node else (params_node.end_point if params_node else function_node.start_point))
    signature_range = SourceRange(
        lineno=function_node.start_point.row + 1,
        end_lineno=end_point.row + 1,
        col_offset=function_node.start_point.column,
        end_col_offset=end_point.column
    )

    return Signature(
        signature_range=signature_range,
        arguments_range=arguments_range,
        return_type_range=return_type_range
    )

def _select_variable_declaration_type(name: str) -> type[VariableDeclaration]:
    if name.isupper() and len(name) > 0:
        return PythonConstant
    return VariableDeclaration

def collect_from_assignment_node(node: Node) -> list[VariableDeclaration]:
    variables: list[VariableDeclaration] = []

    source_range = create_source_range(node)

    left = node.child_by_field_name("left")
    name = node_text(left)
    left_range = create_source_range(left) if left else None

    if node.type == "assignment":
        if left and left.type in ("pattern_list", "tuple_pattern"):
            right = node.child_by_field_name("right")
            value_range = create_source_range(right) if right else None
            variable_binding = ComplexBinding(
                source_range=left_range,
            )

            variable_declaration_type = _select_variable_declaration_type(name)
            variables.append(
                variable_declaration_type(
                    variable_binding=variable_binding,
                    source_range=source_range,
                    value_range=value_range,
                    type_annotation=None,
                )
            )
            
        elif left and left.type == "identifier":
            variable_binding = SimpleBinding(
                name=name
            )

            right = node.child_by_field_name("right")
            value_range = create_source_range(right) if right else None

            type_node = node.child_by_field_name("type")
            type_range = create_source_range(type_node) if type_node else None

            variable_declaration_type = _select_variable_declaration_type(name)
            variables.append(
                variable_declaration_type(
                    type_annotation=type_range,
                    variable_binding=variable_binding,
                    source_range=source_range,
                    value_range=value_range,
                )
            )

    elif node.type == "annotated_assignment":
        if left and left.type == "identifier":
            variable_binding = SimpleBinding(
                name=name
            )

            value_node = node.child_by_field_name("right")
            value_range = create_source_range(value_node) if value_node else None

            type_node = node.child_by_field_name("type")
            type_range = create_source_range(type_node) if type_node else None

            variable_declaration_type = _select_variable_declaration_type(name)
            variables.append(
                variable_declaration_type(
                    variable_binding=variable_binding,
                    source_range=source_range,
                    value_range=value_range,
                    type_annotation=type_range,
                )
            )

    elif node.type == "type_alias_statement":
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value")
        if name_node:
            name = node_text(name_node)
            variable_binding = SimpleBinding(
                name=name
            )
            value_range = create_source_range(value_node) if value_node else None

            variables.append(
                PythonTypeAlias(
                    variable_binding=variable_binding,
                    source_range=source_range,
                    value_range=value_range,
                    type_annotation=None,
                )
            )
    
    return variables