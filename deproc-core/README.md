# deproc-core

`deproc-core` provides the language-agnostic contracts and runtime used by the
deproc source-analysis plugins.

It supplies the shared pipeline for discovering source files, registering
entities, linking package hierarchies, and resolving symbols. Language-specific
parsing and semantics live in separate plugin packages such as
[`deproc-python`](https://pypi.org/project/deproc-python/) and
[`deproc-java`](https://pypi.org/project/deproc-java/).

## Installation

```bash
python -m pip install deproc-core
```

`deproc-core` supports Python 3.12 and newer.

## Core concepts

- `Context` is the central registry for language plugins, parsers, linkers,
  resolvers, symbol caches, and entities.
- `AnalysisScope` describes the permitted analysis universe, including project,
  source, generated, declaration, and dependency roots, selected languages and
  extensions, exclusions, and root provenance.
- `EntityRegistry` stores entities by ID and maintains a fully qualified
  name-to-ID index for entities with FQNs.
- `SourceParser`, `Linker`, `Resolver`, and `SymbolCache` are the protocols
  implemented by language plugins.

## Example

```python
from deproc.core.context import Context
from deproc.core.discovery import find_source_files
from deproc.core.scope import AnalysisScope

scope = AnalysisScope(project_roots=["/path/to/project"])
context = Context(scope=scope)
context.set_language("python", [".py", ".pyi"], aliases=["py"])

files = find_source_files(context)
```

Plugins register their parser, linker, and resolver implementations with the
context, and may optionally register a symbol cache.

## Analysis roots

An `AnalysisScope` groups roots by kind: `project_roots`, `source_roots`,
`generated_roots`, `declaration_roots`, and `dependency_roots`. Each root has a
`root_id`, either supplied by the caller (unique within a scope) or derived from
the kind and the path, for example `source-2a8a187fbe5f19b4`.

`selected_languages`, `selected_file_extensions`, and `exclusions` narrow the
scope. A selection that is passed is authoritative: registering a plugin does
not widen it, and an explicitly empty selection selects nothing. A selection
that is omitted means every registered language and extension. Exclusion
patterns use shell-style wildcards and match file and directory names.

`discover_source_files(context)` returns `DiscoveredFile` objects that carry
`path`, `relative_path`, `root`, `root_kind`, `root_id`, and `provenance`.
`find_source_files(context)` returns only the paths. When roots overlap, each
file is reported once, under the preferred root, chosen in this order:

1. the most specific root, meaning the deepest path
2. the kind order `project`, `source`, `generated`, `declaration`, `dependency`
3. explicit provenance before configured provenance
4. the root id

## Parsing and linking several roots

Parse and link each root with its own context and set `Context.source_root_id`
to that root's `root_id`. Physical nodes then derive their IDs from the root
identity and the path, so a file with the same relative path and contents in two
roots gets a different ID in each. Without `source_root_id` the IDs are the
same as for a single root.

Package-like entities that several roots can contribute to, such as Python
namespace packages and Java packages, are `SemanticContainer` objects.
`EntityRegistry.add()` raises `ValueError` if it would replace one with another
object. Combine the per-root registries with `EntityRegistry.merge_from()`, or
add a single container with `merge_semantic_container()`. Both merge the
contributions instead of replacing them.

## Related packages

- [`deproc-python`](https://pypi.org/project/deproc-python/) — Python parsing,
  linking, and semantic resolution.
- [`deproc-java`](https://pypi.org/project/deproc-java/) — Java parsing,
  linking, and semantic resolution.
- [`deproc-utils-tree-sitter`](https://pypi.org/project/deproc-utils-tree-sitter/)
  — shared tree-sitter utilities.
- [`deproc-utils-python-env`](https://pypi.org/project/deproc-utils-python-env/)
  — Python environment discovery utilities.

## Development

Source code and tests are maintained in the
[deproc repository](https://github.com/gurveervirk/deproc).

```bash
uv sync
uv run pytest deproc-core/tests
```

`deproc-core` is released under the Apache-2.0 license.
