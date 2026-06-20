from tree_sitter import Node, TreeCursor
from typing import Iterable

def iter_children(node: Node | None) -> Iterable[Node]:
    if not node:
        return
    cursor: TreeCursor = node.walk()
    if not cursor.goto_first_child():
        return
    while True:
        yield cursor.node
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
            yield cursor.node
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