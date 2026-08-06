from tree_sitter import (
    Language,
    Node,
    Parser
)
from ..models import SourceRange
import tree_sitter_java

def get_java_language() -> Language:
    return Language(tree_sitter_java.language())

def get_java_parser() -> Parser:
    parser = Parser(get_java_language())
    return parser

def node_text(node: Node | None) -> str:
    if not node:
        return ""
    return node.text.decode("utf-8")

def create_source_range(node: Node, source_id: str | None = None) -> SourceRange:
    return SourceRange(
        lineno=node.start_point.row + 1,
        end_lineno=node.end_point.row + 1,
        col_offset=node.start_point.column,
        end_col_offset=node.end_point.column,
        source_id=source_id,
    )
