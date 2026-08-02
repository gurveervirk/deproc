---
name: deproc
description: Use deproc Python library for programmatic source code analysis — parse files into entities, link package hierarchies, resolve symbols across modules. USE FOR: building code analysis tools, language servers, documentation generators, static analysis. DO NOT USE FOR: editing code directly.
metadata:
  category: source-code-analysis
  language: python
---

# deproc — Source Code Analysis Framework

## Packages

| Package | Purpose |
|---|---|
| `deproc-core` | Plugin interfaces, entity models, context, entity registry |
| `deproc-python` | Python language plugin (tree-sitter based) |
| `deproc-utils-tree-sitter` | Shared tree-sitter AST walking utilities |

## Installation
```bash
pip install deproc-core deproc-python deproc-utils-tree-sitter
```

## Quick start

```python
from deproc.core.context import Context
from deproc.core.discovery import find_source_files
from deproc.plugins.python import (
    PythonSourceParser, PythonLinker, PythonResolver, PythonSymbolCache,
)

ctx = Context(base_path="/path/to/project")
ctx.set_language("python", [".py", ".pyi"], aliases=["py"])
ctx.set_parser("python", PythonSourceParser())
ctx.set_linker("python", PythonLinker())
ctx.set_resolver("python", PythonResolver())
ctx.set_symbol_cache("python", PythonSymbolCache())

files = find_source_files(ctx)
parser = ctx.get_parser("python")
modules = [parser.parse_file(f, ctx) for f in files]
root = ctx.get_linker("python").link_files(modules, ctx)
result = ctx.get_resolver("python").resolve("mymodule", "MyClass", ctx)
```

## Learn more

- **Building a language plugin?** See `deproc-core` skill — covers `Context`, `EntityRegistry`, protocol interfaces (`SourceParser`, `Linker`, `Resolver`, `SymbolCache`), and entity models.
- **Using deproc for Python analysis?** See `deproc-python` skill — covers Python plugin setup, Python-specific models, and MRO/inheritance utilities.

## When to use me
- Building a code intelligence tool or language server
- Creating documentation generators from source
- Implementing static analysis or linting tools
- Building custom code indexers or search tools
