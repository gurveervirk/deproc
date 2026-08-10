# deproc-java

Java language plugin for [deproc](https://github.com/gurveervirk/deproc).

Parses `.java` files using tree-sitter, builds a hierarchical package graph, and indexes all type definitions for use by downstream tools.

## Features

- Parse Java source files into the deproc entity model
- Build a package hierarchy from `package` declarations
- Fully qualified name (FQN) resolution via the entity registry
- Common Java constructs: classes, interfaces, enums, records, annotations, methods, fields, constructors
- Short-name resolution (`resolver/`) and per-compilation-unit symbol caching (`symbol_cache/`)

## Install

```bash
uv add deproc-java
```

## Usage

```python
from deproc.core.context import Context
from deproc.plugins.java import (
    JavaSourceParser,
    JavaLinker,
    JavaResolver,
    JavaSymbolCache,
)

ctx = Context(base_path="/path/to/src/main/java")
ctx.set_language("java", ["java"])

parser = JavaSourceParser()
cu = parser.parse_file("/path/to/src/main/java/com/example/Foo.java", ctx)

linker = JavaLinker()
packages = linker.link_files([cu], ctx)

ctx.set_resolver("java", JavaResolver())
ctx.set_symbol_cache(JavaSymbolCache())

result = ctx.get_resolver("java").resolve("com.example.Foo", "List", ctx)
# JavaResolverResult(resolved_ids={...}, unresolved_ids={...})
```

## Package layout

```
deproc-java/
├── deproc/plugins/java/
│   ├── parser/         JavaSourceParser (tree-sitter AST → entities)
│   ├── linker/         JavaLinker (compilation units → package hierarchy)
│   ├── resolver/       JavaResolver (short name → FQN via imports)
│   ├── symbol_cache/   JavaSymbolCache (per-compilation-unit cache)
│   └── utils/          resolve_java_import, entity serialization
└── tests/
```

## Dependencies

- `deproc-core` (entity model, Context, EntityRegistry)
- `deproc-utils-tree-sitter` (AST walking utilities)
- `tree-sitter-java` (Java grammar)
