from deproc.utils.tree_walk import iter_children
from tree_sitter import Node

from ..models import (
    Annotation,
    JavaParameter,
    Signature,
    SourceRange,
)
from .tree_sitter_java import (
    create_source_range,
    node_text,
)


def is_javadoc(node: Node) -> bool:
    if node.type != "block_comment" or node.text is None:
        return False
    text = node.text.decode("utf-8")
    return text.startswith("/**")


def extract_javadoc_range(
    node: Node, source_file_id: str | None = None
) -> SourceRange | None:
    parent = node.parent
    if parent is None:
        return None
    previous: Node | None = None
    for child in iter_children(parent):
        if child.id == node.id:
            break
        if child.type in ("block_comment", "line_comment", "comment"):
            previous = child
        else:
            previous = None
    if previous is not None and is_javadoc(previous):
        return create_source_range(previous, source_id=source_file_id)
    return None


def extract_annotations(
    modifiers_node: Node | None, source_file_id: str | None = None
) -> list[Annotation]:
    annotations: list[Annotation] = []
    if modifiers_node is None:
        return annotations
    for child in iter_children(modifiers_node):
        if child.type in ("annotation", "marker_annotation"):
            name_node = child.child_by_field_name("name")
            annotations.append(
                Annotation(
                    name=node_text(name_node) if name_node else node_text(child),
                    source_range=create_source_range(child, source_id=source_file_id),
                )
            )
    return annotations


def type_text(node: Node | None) -> str:
    if node is None:
        return ""
    if node.type == "generic_type":
        inner = node.child_by_field_name("type")
        return type_text(inner)
    return node_text(node)


def extract_type_names(node: Node | None) -> list[str]:
    if node is None:
        return []
    names: list[str] = []
    for child in iter_children(node):
        if child.type in ("type_identifier", "scoped_type_identifier", "generic_type"):
            names.append(type_text(child))
        elif child.type == "type_list":
            names.extend(extract_type_names(child))
    return names


def extract_signature(node: Node, source_file_id: str | None = None) -> Signature:
    name_node = node.child_by_field_name("name")
    params_node = node.child_by_field_name("parameters")
    type_node = node.child_by_field_name("type")

    arguments_range = (
        create_source_range(params_node, source_id=source_file_id)
        if params_node
        else None
    )
    return_type_range = (
        create_source_range(type_node, source_id=source_file_id) if type_node else None
    )

    if params_node is not None:
        end_point = params_node.end_point
    elif name_node is not None:
        end_point = name_node.end_point
    else:
        end_point = node.end_point

    signature_range = SourceRange(
        lineno=node.start_point.row + 1,
        end_lineno=end_point.row + 1,
        col_offset=node.start_point.column,
        end_col_offset=end_point.column,
        source_id=source_file_id,
    )

    return Signature(
        signature_range=signature_range,
        arguments_range=arguments_range,
        return_type_range=return_type_range,
    )


def extract_parameters(
    node: Node, source_file_id: str | None = None
) -> list[JavaParameter]:
    parameters: list[JavaParameter] = []
    params_node = node.child_by_field_name("parameters")
    if params_node is None:
        return parameters

    for child in iter_children(params_node):
        if child.type not in ("formal_parameter", "spread_parameter"):
            continue

        name_node = child.child_by_field_name("name")
        type_node = child.child_by_field_name("type")

        if child.type == "spread_parameter":
            if type_node is None:
                for sub in iter_children(child):
                    if sub.type in (
                        "type_identifier",
                        "scoped_type_identifier",
                        "generic_type",
                    ):
                        type_node = sub
                        break
            declarator = first_child_of_type(child, "variable_declarator")
            if declarator is not None:
                name_node = declarator.child_by_field_name("name")

        modifiers_node = child.child_by_field_name("modifiers")
        modifier_names: list[str] = []
        from .misc import extract_modifier_names

        if modifiers_node is not None:
            modifier_names = extract_modifier_names(modifiers_node)

        parameters.append(
            JavaParameter(
                name=node_text(name_node),
                type_fqn=type_text(type_node),
                is_final="final" in modifier_names,
                is_varargs=child.type == "spread_parameter",
                source_range=create_source_range(child, source_id=source_file_id),
            )
        )
    return parameters


def first_child_of_type(node: Node, node_type: str) -> Node | None:
    for child in iter_children(node):
        if child.type == node_type:
            return child
    return None


def extract_exceptions(node: Node) -> list[str]:
    exceptions: list[str] = []
    throws_node = first_child_of_type(node, "throws")
    if throws_node is None:
        return exceptions
    for child in iter_children(throws_node):
        if child.type in ("type_identifier", "scoped_type_identifier", "generic_type"):
            exceptions.append(type_text(child))
    return exceptions
