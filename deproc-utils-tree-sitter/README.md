# deproc-utils-tree-sitter

Tree-sitter AST walking utilities shared by the
[deproc](https://github.com/gurveervirk/deproc) language plugins.

## Install

```bash
python -m pip install deproc-utils-tree-sitter
```

`deproc-utils-tree-sitter` supports Python 3.10 and newer. It requires
`tree-sitter>=0.25.2,<0.26`.

## Usage

```python
import tree_sitter_python
from tree_sitter import Language, Parser

from deproc.utils.tree_walk import first_child, iter_children, walk_preorder

parser = Parser(Language(tree_sitter_python.language()))
tree = parser.parse(b"class Invoice:\n    def total(self):\n        return 0\n")

[child.type for child in iter_children(tree.root_node)]  # ['class_definition']
first_child(tree.root_node).type  # 'class_definition'
[
    node.type
    for node in walk_preorder(tree.root_node)
    if node.type.endswith("definition")
]
# ['class_definition', 'function_definition']
```

The grammar package (`tree-sitter-python` above) is not a dependency; install the
one for the language you parse.

## API

`deproc.utils.tree_walk` provides cursor-based helpers that accept `None` and
yield nothing for it:

- `iter_children(node)` yields the direct children of `node`.
- `first_child(node)` returns the first child, or `None`.
- `walk_preorder(node)` yields `node` and all its descendants in pre-order.
