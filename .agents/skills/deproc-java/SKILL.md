---
name: deproc-java
description: Java language plugin for deproc — parse Java files into entities, build package hierarchies, resolve types across compilation units. USE FOR: analyzing Java source code, building Java code intelligence tools, working with named modules. DO NOT USE FOR: general Java editing, creating new language plugins (use deproc-core skill instead).
metadata:
  category: source-code-analysis
  language: python
---

# deproc-java — Java Language Plugin

## Package
```bash
pip install deproc-java deproc-core
```

## Setup
```python
from deproc.core.context import Context
from deproc.core.discovery import find_source_files
from deproc.plugins.java import (
    JavaLinker,
    JavaResolver,
    JavaSourceParser,
    JavaSymbolCache,
)

ctx = Context(base_path="/path/to/src/main/java")
ctx.set_language("java", [".java"])
ctx.set_parser("java", JavaSourceParser())
ctx.set_linker("java", JavaLinker())
ctx.set_resolver("java", JavaResolver())
ctx.set_symbol_cache(JavaSymbolCache())
```

`set_symbol_cache()` takes only the cache. The cache carries its own language.

## Pipeline
```python
files = find_source_files(ctx)
parser = ctx.get_parser("java")
units = [parser.parse_file(f, ctx) for f in files]
packages = ctx.get_linker("java").link_files(units, ctx)
result = ctx.get_resolver("java").resolve("com.acme.Foo", "Helper", ctx)
```

`link_files` returns the root `JavaPackage` objects. Every entity is also in `ctx.entity_registry`, indexed by FQN.

## Java entity models

| Model | Purpose |
|---|---|
| `JavaCompilationUnit` | Parsed `.java` file, has `fqn` and `package_fqn` |
| `JavaPackageInfo` | `package-info.java`, has `annotations` |
| `JavaPackage` | Package built by the linker, has `subpackage_ids`, `compilation_unit_ids`, `package_info_ids`, `module_name` |
| `JavaClass`, `JavaInterface`, `JavaEnum`, `JavaRecord`, `JavaAnnotationType` | Type definitions |
| `JavaMethod`, `JavaField` | Methods, constructors and fields |
| `JavaEnumConstant`, `JavaRecordComponent` | Enum constants and record components |
| `JavaImport` | Import declaration |
| `JavaModule` | `module-info.java`, has `module_name`, `requires`, `requires_static`, `requires_transitive`, `exports`, `qualified_exports`, `opens`, `qualified_opens`, `uses`, `provides` |

Model classes live in `deproc.plugins.java.parser.models` and `deproc.plugins.java.linker.models`.

## Named modules

A package declared under a named module belongs to that module. Two modules that both declare `com.acme` give two `JavaPackage` entities, each listing only its own compilation units, with `module_name` set. Code outside any named module keeps one package per name. `JavaPackage` is a `SemanticContainer`: when several roots contribute to the same package, merge the per-root registries with `EntityRegistry.merge_from()`. See the `deproc-core` skill.

## Resolving

```python
resolver = ctx.get_resolver("java")

result = resolver.resolve("com.acme.Foo", "Helper", ctx)
# result.resolved_ids, result.unresolved_ids, result.ambiguous_ids, result.inaccessible_ids
# result.status: RESOLVED, UNRESOLVED, AMBIGUOUS or INACCESSIBLE
# result.reason: str | None

ref = resolver.resolve_type_reference("Helper", owner_type, ctx)
# ref.status, ref.value (the resolved SymbolID), ref.candidates, ref.reason
```

- `resolve(compilation_unit_fqn, symbol_name, ctx)` looks a short name up through one compilation unit's imports. It returns a `JavaResolverResult`.
- `resolve_type_reference(raw_name, owner, ctx)` resolves a type name as written inside `owner`, a type entity such as a `JavaClass`. It returns a `ResolutionResult[SymbolID]`.
- `INACCESSIBLE` means matching types exist but none is visible from the caller.
- `ResolutionStatus` and `ResolutionResult` come from `deproc.core.interfaces.resolver` and are shared with the Python plugin.

## Entity serialization

```python
from deproc.plugins.java.utils.serialization import entity_to_record, record_to_entity

record = entity_to_record(entity, registry=ctx.entity_registry)
# → {"id", "language", "full_path", "name", "type", "metadata_json", "parent_id"}

entity = record_to_entity(record)  # → Entity or None
```

Records round-trip: `record_to_entity(entity_to_record(e)).id == e.id`.

## Tree-sitter integration

`JavaSourceParser` uses tree-sitter (bounded to `>=0.25.2,<0.26`) and `tree-sitter-java`. AST walking utilities are in `deproc-utils-tree-sitter`.

## When to use me
- Analyzing Java source code statically
- Building Java-specific code intelligence tools
- Working with Java packages, named modules and type resolution
