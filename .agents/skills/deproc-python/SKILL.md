---
name: deproc-python
description: Python language plugin for deproc — parse Python files into entities, build package hierarchies, resolve symbols across modules. USE FOR: analyzing Python source code, building Python code intelligence tools, working with Python ASTs. DO NOT USE FOR: general Python editing, creating new language plugins (use deproc-core skill instead).
metadata:
  category: source-code-analysis
  language: python
---

# deproc-python — Python Language Plugin

## Package
```bash
pip install deproc-python deproc-core
```

## Setup
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
```

## Pipeline
```python
files = find_source_files(ctx)
parser = ctx.get_parser("python")
modules = [parser.parse_file(f, ctx) for f in files]
root = ctx.get_linker("python").link_files(modules, ctx)
result = ctx.get_resolver("python").resolve("mymodule", "MyClass", ctx)
```

## Python entity models

| Model | Purpose |
|---|---|
| `PythonModule` | Parsed `.py`/`.pyi` file, has `fqn`, `all_exports` |
| `PythonClass` | Class with `parent_classes`, `method_ids`, `inner_type_ids`, `property_ids` |
| `PythonFunctionLike` | Function/method with `annotations`, `visibility` |
| `PythonConstant` | Module-level constant |
| `PythonTypeAlias` | Type alias (`type X = ...`) |
| `PythonImportStatement` | Import statement, has `path`, `name_ids`, `wildcard` |
| `PythonImportAlias` | Imported name with optional alias, has `original_name` via metadata |
| `PythonPackage` | Directory with `__init__.py`, has `submodule_ids` |
| `PythonNamespacePackage` | Implicit namespace package (no `__init__.py`) |

## MRO / inheritance utilities

```python
from deproc.plugins.python.utils.mro import c3_merge, compute_mro_from_bases

# C3 linearization merge
c3_merge([["B", "O"], ["C", "O"], ["B", "C"]])  # → ["B", "C", "O"]

# Compute MRO from pre-resolved base MROs
compute_mro_from_bases(
    self_fqn="Child",
    base_mros={"Base": ["Base", "object"]},
    base_fqns=["Base"],
)  # → ["Child", "Base", "object"]
```

## Module exports

```python
from deproc.plugins.python.utils.exports import build_module_exports

exports = build_module_exports(registry)  # → {"pkg.mod": {"ClassA", "func"}}
```

## Relative import resolution

```python
from deproc.plugins.python.utils.imports import resolve_relative_import_path

resolve_relative_import_path(".sibling", "pkg.sub.mod", False)  # → "pkg.sub.sibling"
resolve_relative_import_path("..other", "package.subpackage", True)  # → "package.other"
```

Pure function — takes `relative_path`, `parent_fqn`, `parent_is_package` and returns the resolved absolute FQN string.

## Entity serialization

```python
from deproc.plugins.python.utils.serialization import (
    TYPE_TO_CLASS,
    entity_to_record,
    record_to_entity,
)

record = entity_to_record(entity, module_exports=exports, registry=registry)
# → {"id", "language", "full_path", "name", "type", "metadata_json", "parent_id"}

entity = record_to_entity(record)  # → Entity or None
```

## Resolver result type

```python
from deproc.plugins.python.resolver.models import PythonResolverResult

result: PythonResolverResult = resolver.resolve("mymodule", "MyClass", ctx)
# result.resolved_ids: set[SymbolID]
# result.unresolved_ids: set[SymbolID]
```

## Tree-sitter integration

`PythonSourceParser` uses tree-sitter (pinned to `0.25.2` — `0.26.0` causes segfaults). AST walking utilities in `deproc-utils-tree-sitter`:

```python
from deproc.utils import iter_children, first_child, walk_preorder
```

## When to use me
- Analyzing Python source code statically
- Building Python-specific code intelligence tools
- Working with Python ASTs and entity models
- Understanding Python class hierarchies and MRO
