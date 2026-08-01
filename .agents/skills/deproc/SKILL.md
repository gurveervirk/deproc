---
name: deproc
description: Use deproc Python library for programmatic source code analysis — parse files into entities, link package hierarchies, resolve symbols across modules. USE FOR: building code analysis tools, language servers, documentation generators, static analysis. DO NOT USE FOR: editing code directly.
metadata:
  category: source-code-analysis
  language: python
---

# deproc — Source Code Analysis Framework

## Installation
```bash
pip install deproc-core deproc-python deproc-utils-tree-sitter
```

## Core interfaces
- **SourceParser** — `parse_file(path, ctx)` → `SourceFile` with entities
- **Linker** — `link_files(modules, ctx)` → hierarchical package tree
- **Resolver** — `resolve(module, symbol, ctx)` → entity IDs
- **SymbolCache** — `get`/`set` for caching results

## Basic pipeline
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

## When to use me
- Building a code intelligence tool or language server
- Creating documentation generators from source
- Implementing static analysis or linting tools
- Building custom code indexers or search tools
