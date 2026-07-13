# deproc

`deproc` is a modular framework for analyzing source code across programming languages. It provides a pipeline for parsing source files into structured entities (classes, functions, variables, imports), linking them into a package hierarchy, and resolving symbol references across modules.

## Installation

```bash
# Core library (language-agnostic interfaces and runtime)
pip install deproc-core

# Python plugin (tree-sitter-based parser, linker, and resolver)
pip install deproc-python
```

### Dependencies

- Python >= 3.10
- `deproc-python` requires `tree-sitter>=0.25.0` and `tree-sitter-python>=0.25.0`

## Quick Start

```python
from deproc.core.context import Context
from deproc.core.discovery import find_source_files
from deproc.plugins.python import PythonSourceParser, PythonLinker, PythonResolver, PythonSymbolCache

# 1. Create a context and register the Python language
ctx = Context(base_path="/path/to/your/project")
ctx.set_language("python", [".py", ".pyi"], aliases=["py"])
ctx.set_skip_paths({".venv", "__pycache__", ".git"})

# 2. Register plugin components
ctx.set_parser("python", PythonSourceParser())
ctx.set_linker("python", PythonLinker())
ctx.set_resolver("python", PythonResolver())
ctx.set_symbol_cache("python", PythonSymbolCache())

# 3. Discover and parse all Python files
files = find_source_files(ctx)
parser = ctx.get_parser("python")
modules = [parser.parse_file(f, ctx) for f in files]

# 4. Link files into a package hierarchy
linker = ctx.get_linker("python")
root = linker.link_files(modules, ctx)

# 5. Resolve a symbol
resolver = ctx.get_resolver("python")
result = resolver.resolve("mymodule", "MyClass", ctx)
print(f"Resolved IDs: {result.resolved_ids}")
print(f"Unresolved IDs: {result.unresolved_ids}")
```

## Architecture

```
User Code
    |
    v
 Context (central hub)
    |
    +-- find_source_files() --> file paths
    +-- parser.parse_file(path, ctx) --> Module (entities registered in ctx.entity_registry)
    +-- linker.link_files(modules, ctx) --> linked Node tree with parent/child relationships
    +-- resolver.resolve(module, symbol, ctx) --> resolved and unresolved symbol IDs
    +-- symbol_cache.get/set --> cache layer for resolution results
```

The framework is built around four core interfaces:

### SourceParser

Parses a source file into structured entities (classes, functions, variables, imports, control flow). All extracted entities are registered in the `EntityRegistry` on the context.

```python
class SourceParser(Protocol):
    def parse_file(self, file_path: str, context: Context) -> SourceFile: ...
```

### Linker

Takes a flat list of parsed modules and builds a hierarchical package tree. Sets `parent_id` on child nodes and `submodule_ids` on parent packages.

```python
class Linker(Protocol[T_In, T_Out]):
    def link_files(self, nodes: T_In, context: Context) -> T_Out: ...
```

### Resolver

Resolves a symbol name within a module to its entity IDs. Follows import aliases transitively, handling circular references. Caches results in the symbol cache.

```python
class Resolver(Protocol[TOut]):
    def resolve(self, *args, **kwargs) -> TOut: ...
```

### SymbolCache

Bidirectional cache mapping `(module_fqn, symbol_name)` keys to `(resolved_ids, unresolved_ids)` pairs. Supports module-level invalidation.

```python
class SymbolCache(Protocol[TCache, TReturn]):
    language: str
    def get(self, *args, **kwargs) -> TReturn: ...
    def set(self, *args, **kwargs) -> None: ...
```

## Project Structure

```
deproc/
  deproc-core/                   # Core interfaces, context, entity registry, file discovery
    deproc/core/
      context.py                 # Context -- central hub for config and plugins
      discovery.py               # find_source_files()
      interfaces/
        parser/base.py           # SourceParser protocol
        parser/models.py         # Entity, Node, SourceFile, FunctionLike, TypeDefinition, etc.
        linker.py                # Linker protocol
        resolver.py              # Resolver protocol
        symbol_cache.py          # SymbolCache protocol
      runtime/registries/
        entity.py                # EntityRegistry (in-memory entity store with FQN index)

  deproc-python/                 # Python language plugin
    deproc/plugins/python/
      parser/                    # PythonSourceParser (tree-sitter based)
      linker/                    # PythonLinker (package hierarchy builder)
      resolver/                  # PythonResolver (symbol resolution with caching)
      symbol_cache/              # PythonSymbolCache (bidirectional FQN cache)

  deproc-utils-tree-sitter/      # Shared tree-sitter tree-walking utilities
    deproc/utils/
      tree_walk.py               # iter_children, first_child, walk_preorder
```

## Core Concepts

### Entity Model

All code elements (classes, functions, variables, imports) are `Entity` instances with deterministic IDs:

- **Entity IDs**: UUID5 derived from `(parent_id, type_qualname, source_range)` -- same code always produces the same ID.
- **Node IDs** (files, directories): UUID5 derived from `file://path`.
- **EntityRegistry**: In-memory store with automatic FQN-to-ID indexing for fast lookups.

### FQN (Fully Qualified Name)

Entities carry an `fqn` field (e.g., `mypackage.mymodule.MyClass`). The resolver uses the FQN index to find entities by name without walking import trees. Import aliases also carry `fqn` set at parse time.

### Deterministic IDs

When `parent_id` and `source_range` are both set, entity IDs are deterministic across runs. This enables caching, diffing, and reproducible analysis.

## Writing a Language Plugin

1. Implement `SourceParser` -- produce `SourceFile` with extracted entities.
2. Implement `Linker` -- build a hierarchy from parsed modules.
3. Implement `Resolver` -- resolve symbols using the entity registry's FQN index.
4. Implement `SymbolCache` (optional) -- cache resolution results.
5. Register with `Context`:

```python
ctx.set_parser("mylang", MyParser())
ctx.set_linker("mylang", MyLinker())
ctx.set_resolver("mylang", MyResolver())
ctx.set_symbol_cache("mylang", MySymbolCache())
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run all tests
uv run pytest

# Run tests for a specific package
uv run pytest deproc-python/tests/
uv run pytest deproc-core/tests/
```
