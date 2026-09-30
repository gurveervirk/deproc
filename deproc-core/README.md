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
