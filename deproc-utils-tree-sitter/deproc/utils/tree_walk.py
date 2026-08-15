from collections.abc import Iterable

from tree_sitter import Node, TreeCursor


def iter_children(node: Node | None) -> Iterable[Node]:
    if not node:
        return
    cursor: TreeCursor = node.walk()
    if not cursor.goto_first_child():
        return
    while True:
        child = cursor.node
        if child is not None:
            yield child
        if not cursor.goto_next_sibling():
            break


def first_child(node: Node | None) -> Node | None:
    for child in iter_children(node):
        return child
    return None


def walk_preorder(node: Node | None) -> Iterable[Node]:
    if not node:
        return
    cursor: TreeCursor = node.walk()
    visited = False
    while True:
        if not visited:
            node_at_cursor = cursor.node
            if node_at_cursor is not None:
                yield node_at_cursor
            if cursor.goto_first_child():
                visited = False
                continue
            visited = True
        if cursor.goto_next_sibling():
            visited = False
            continue
        if not cursor.goto_parent():
            break
        visited = True
