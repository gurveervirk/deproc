from tree_sitter import (
    Language,
    Node,
    Parser
)
from ..models import SourceRange
import tree_sitter_python

def get_python_language() -> Language:
    return Language(tree_sitter_python.language())

def get_python_parser() -> Parser:
    PY_LANGUAGE = get_python_language()
    parser = Parser(PY_LANGUAGE)
    return parser
    
def node_text(node: Node) -> str:
    if not node:
        return ""
    return node.text.decode("utf-8")

def create_source_range(node: Node) -> SourceRange:
    return SourceRange(
        lineno=node.start_point.row + 1,
        end_lineno=node.end_point.row + 1,
        col_offset=node.start_point.column,
        end_col_offset=node.end_point.column
    )