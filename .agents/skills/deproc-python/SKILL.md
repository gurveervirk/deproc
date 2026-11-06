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
    PythonSourceParser,
    PythonLinker,
    PythonResolver,
    PythonSymbolCache,
)

ctx = Context(base_path="/path/to/project")
ctx.set_language("python", [".py", ".pyi"], aliases=["py"])
ctx.set_parser("python", PythonSourceParser())
ctx.set_linker("python", PythonLinker())
ctx.set_resolver("python", PythonResolver())
ctx.set_symbol_cache(PythonSymbolCache())
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
| `PythonNamespacePackage` | Implicit namespace package (no `__init__.py`); a `SemanticContainer` that merges the portions from every root |

## Several roots

`files_by_root` maps each `RootDescriptor` to the `DiscoveredFile` objects that `discover_source_files(ctx)` returned for it.

```python
from deproc.core.runtime import EntityRegistry
from deproc.plugins.python.utils.packages import apply_regular_package_precedence

registries = []
for root, found_files in files_by_root.items():
    root_ctx = Context(copy_from=ctx, source_root_id=root.root_id)
    root_ctx.base_path = root.path
    root_ctx.entity_registry = EntityRegistry()
    modules = [parser.parse_file(f.path, root_ctx) for f in found_files]
    linker.link_files(modules, root_ctx)
    registries.append(root_ctx.entity_registry)

shadowed = apply_regular_package_precedence(registries)
merged = EntityRegistry()
for registry in registries:
    merged.merge_from(registry)
```

- A namespace package contributed by several roots becomes one `PythonNamespacePackage` after `merge_from()`.
- `apply_regular_package_precedence()` applies Python's import rule: a regular package (`__init__.py`) in one root wins over a same-named namespace portion, or one under it, in another root. Call it on the per-root registries before merging. The shadowed container is removed, its modules stay in the registry with `parent_id = None`, and the returned `ShadowedNamespacePortion` objects (`fqn`, `path`, `registry_index`, `detached_ids`) say what was detached. A warning is logged on `deproc.plugins.python.utils.packages`.
- `apply_regular_package_precedence()` compares separate per-root registries. To link several roots into one registry instead, give each root's context its `source_root_id` and reuse one `entity_registry`. `PythonLinker.link_files()` then applies the same rule to the whole registry after every call, in any root order, and drops the removed containers from the nodes it returns. `apply_regular_package_precedence_to_registry(registry)` does the same on demand, for example on registries combined with `merge_from()`, and calling it again changes nothing.
- `PythonLinker(apply_package_precedence=False)` turns the automatic pass off. The linker then neither prunes the registry nor logs the same-name warning, and you can still call `apply_regular_package_precedence_to_registry()` yourself. The default is `True`.
- A nested namespace portion, such as `acme.sub` in a root other than the one holding the regular `acme`, is only detected when the roots have different `source_root_id` values. Without them only a portion whose name is exactly the regular package's name is removed.
- Two regular packages with the same name in different roots are both kept, because Python would import only the first on its path. `find_regular_package_conflicts(registries)` lists them as `RegularPackageConflict` objects (`fqn`, `source_root_ids`), and both precedence functions log a warning for each one.

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

## Resolver result types

```python
from deproc.core.interfaces.resolver import ResolutionStatus
from deproc.plugins.python.resolver.models import PythonResolverResult

result: PythonResolverResult = resolver.resolve("mymodule", "MyClass", ctx)
# result.resolved_ids: set[SymbolID]
# result.unresolved_ids: set[SymbolID]
# result.ambiguous_ids: set[SymbolID]     # more than one symbol matched
# result.inaccessible_ids: set[SymbolID]
# result.reason: str | None
# result.status: ResolutionStatus         # RESOLVED, UNRESOLVED, AMBIGUOUS or INACCESSIBLE
# result.candidates: tuple[SymbolID, ...]
```

`ResolutionStatus` and the generic `ResolutionResult` live in `deproc.core.interfaces.resolver` and are shared with the Java plugin.

## Class MRO and inherited members

```python
from deproc.plugins.python import PythonClassMROResult, PythonInheritedMembersResult

mro: PythonClassMROResult = resolver.resolve_class_mro(class_id, ctx)
# mro.status: ResolutionStatus
# mro.mro_ids: tuple[SymbolID, ...]       # the C3 order, starting with the class
# mro.bases: tuple[PythonBaseResolution, ...]  # per base: name, status, resolved_id, candidates, reason
# mro.reason: str | None

members: PythonInheritedMembersResult = resolver.get_inherited_members(class_id, ctx)
# members.members: tuple[PythonInheritedMember, ...]  # member_id, owner_id, name, mro_depth
```

- `resolve_class_mro(class_id, ctx, base_overrides=None)` accepts `base_overrides`, a mapping of `(class_id, base_name)` to the entity ID to use for that base. Callers use it to apply their own choice when a base name is ambiguous.
- `get_inherited_members(class_id, ctx, mro_result=None)` reuses an `mro_result` you already computed.
- An unresolved or ambiguous base is reported on the result with its `status` and `reason`, not raised.

## Tree-sitter integration

`PythonSourceParser` uses tree-sitter, bounded to `>=0.25.2,<0.26` because `0.26.0` segfaults on real library code. AST walking utilities in `deproc-utils-tree-sitter`:

```python
from deproc.utils import iter_children, first_child, walk_preorder
```

## When to use me
- Analyzing Python source code statically
- Building Python-specific code intelligence tools
- Working with Python ASTs and entity models
- Understanding Python class hierarchies and MRO
