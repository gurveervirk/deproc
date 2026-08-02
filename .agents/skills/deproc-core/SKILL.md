---
name: deproc-core
description: Core framework for building language analysis plugins with deproc — implement SourceParser, Linker, Resolver, SymbolCache protocols and work with Entity models. USE FOR: creating a new language plugin, extending deproc to support a new language. DO NOT USE FOR: Python analysis (use deproc-python skill instead).
metadata:
  category: source-code-analysis
  language: python
---

# deproc-core — Plugin Framework

## Package
```bash
pip install deproc-core
```

## Architecture

```
Context (central hub)
  ├── set_language()          — register language + file extensions
  ├── set_parser()            — SourceParser for parsing files
  ├── set_linker()            — Linker for building package hierarchy
  ├── set_resolver()          — Resolver for cross-module symbol resolution
  ├── set_symbol_cache()      — SymbolCache for caching results
  └── entity_registry         — EntityRegistry storing all parsed entities
```

## Protocol interfaces

All protocols are `@runtime_checkable` and use `typing.Protocol`.

### SourceParser
```python
from deproc.core.interfaces.parser import SourceParser

class MyParser:  # implements SourceParser
    def parse_file(self, file_path: str, context: Context) -> SourceFile:
        ...
```

### Linker
```python
from deproc.core.interfaces.linker import Linker

class MyLinker:  # implements Linker
    def link_files(self, nodes: list[SourceFile], context: Context) -> list[Node]:
        ...
```

### Resolver
```python
from deproc.core.interfaces.resolver import Resolver

class MyResolver:  # implements Resolver
    def resolve(self, *args: Any, **kwargs: Any) -> TOut:
        ...
```

### SymbolCache
```python
from deproc.core.interfaces.symbol_cache import SymbolCache

class MySymbolCache:  # implements SymbolCache
    language: str = "mylang"
    cache: MyCacheType

    def get(self, *args, **kwargs) -> TReturn: ...
    def set(self, *args, **kwargs) -> None: ...
```

## Entity models

All entities extend `Entity` with deterministic UUID5 IDs derived from `(parent_id, type_qualname, source_range)`:

| Model | Purpose | Key fields |
|---|---|---|
| `Entity` | Base class | `id`, `parent_id` |
| `SourceRange` | Location in source | `lineno`, `end_lineno`, `col_offset`, `end_col_offset`, `source_id` |
| `SourceFile` | Parsed file | `import_stmt_ids`, `type_ids`, `function_ids`, `variable_ids`, `control_flow_group_ids`, `source` |
| `Node` | File/directory in package tree | `path` (ID from `file://path`) |
| `TypeDefinition` | Class/type | `fqn`, `inherits`, `method_ids`, `inner_type_ids`, `property_ids`, `visibility` |
| `FunctionLike` | Function/method | `fqn`, `signature`, `visibility` |
| `VariableDeclaration` | Variable/constant | `variable_binding`, `value_range`, `type_annotation`, `modifiers` |
| `ControlFlowBlock` | If/except branch | `branch`, `import_stmt_ids`, `type_ids`, `function_ids`, `variable_ids` |
| `ControlFlowGroup` | Group of related blocks | `group_type`, `block_ids` |

## EntityRegistry

```python
from deproc.core.runtime import EntityRegistry

registry = EntityRegistry()  # lives on ctx.entity_registry
registry.add(entity)         # stores + indexes by FQN
registry.get(entity_id)      # lookup by ID
registry.get_ids_by_fqn(fqn) # FQN → set of entity IDs
registry.values()            # all entities
```

## File discovery
```python
from deproc.core.discovery import find_source_files

ctx.set_skip_paths({"*.dist-info", "*.egg-info"})
files = find_source_files(ctx)  # list of absolute paths
```

## Pipeline pattern

```python
# 1. Setup
ctx = Context(base_path="/project")
ctx.set_language("mylang", [".myext"])
ctx.set_parser("mylang", MyParser())
ctx.set_linker("mylang", MyLinker())

# 2. Discover
files = find_source_files(ctx)

# 3. Parse
parser = ctx.get_parser("mylang")
modules = [parser.parse_file(f, ctx) for f in files]

# 4. Link
linker = ctx.get_linker("mylang")
root_nodes = linker.link_files(modules, ctx)

# 5. Resolve (per symbol)
resolver = ctx.get_resolver("mylang")
result = resolver.resolve("mymodule", "MyClass", ctx)
```

## When to use me
- Creating a plugin for a new language (Java, TypeScript, Go, etc.)
- Extending deproc's entity model for language-specific features
- Building a custom resolver or symbol cache implementation
