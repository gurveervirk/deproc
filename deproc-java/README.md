# deproc-java

Java language plugin for [deproc](https://github.com/gurveervirk/deproc).

Parses `.java` files using tree-sitter, builds a hierarchical package graph, and indexes all type definitions for use by downstream tools.

## Features

- Parse Java source files into the deproc entity model
- Build a package hierarchy from `package` declarations
- Fully qualified name (FQN) resolution via the entity registry
- Common Java constructs: classes, interfaces, enums, records, annotations, methods, fields, constructors
- Short-name resolution (`resolver/`) and per-compilation-unit symbol caching (`symbol_cache/`)

## Named modules

A package declared under a named module (`module-info.java`) belongs to that
module. Two modules that both declare `com.acme` produce two `JavaPackage`
entities, one per module, each listing only its own compilation units. The owning
module is recorded in `JavaPackage.module_name`. Code outside any named module
keeps one package per name.

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
ctx.set_language("java", [".java"])

parser = JavaSourceParser()
cu = parser.parse_file("/path/to/src/main/java/com/example/Foo.java", ctx)

linker = JavaLinker()
packages = linker.link_files([cu], ctx)

ctx.set_resolver("java", JavaResolver())
ctx.set_symbol_cache(JavaSymbolCache())

result = ctx.get_resolver("java").resolve("com.example.Foo", "List", ctx)
# JavaResolverResult(resolved_ids={...}, unresolved_ids={...}, ...)
```

`JavaResolverResult` also carries `inaccessible_ids`, `ambiguous_ids`, and `reason`, and exposes `status` and `candidates`. `status` is a `ResolutionStatus` (`RESOLVED`, `UNRESOLVED`, `AMBIGUOUS`, or `INACCESSIBLE`) from `deproc.core.interfaces.resolver`.

To resolve a type name as written inside a type, call `resolve_type_reference(raw_name, owner, ctx)`. It returns a `ResolutionResult` whose `status` is `INACCESSIBLE` when matching types exist but none is visible from `owner`.

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
