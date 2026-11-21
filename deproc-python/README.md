# deproc-python

Python language plugin for [deproc](https://github.com/gurveervirk/deproc).

Parses `.py` and `.pyi` files with tree-sitter into the deproc entity model,
links them into a package hierarchy, and resolves names across modules.

## Features

- Modules, classes, functions and methods, constants, type aliases, imports and
  import aliases as deproc entities
- Regular packages (`__init__.py`) and implicit namespace packages, including a
  namespace package contributed by several roots
- Python's regular-package precedence across roots: a regular package wins over
  a same-named namespace portion from another root
- Name resolution through imports, relative imports and wildcard imports
- Class MRO (C3 linearization) and inherited members
- Entity serialization to flat records and back

## Install

```bash
python -m pip install deproc-python
```

`deproc-python` supports Python 3.12 and newer and installs `deproc-core` with it.

## Usage

```python
from deproc.core.context import Context
from deproc.core.discovery import find_source_files
from deproc.plugins.python import (
    PythonLinker,
    PythonResolver,
    PythonSourceParser,
    PythonSymbolCache,
)

ctx = Context(base_path="/path/to/project")
ctx.set_language("python", [".py", ".pyi"], aliases=["py"])
ctx.set_parser("python", PythonSourceParser())
ctx.set_linker("python", PythonLinker())
ctx.set_resolver("python", PythonResolver())
ctx.set_symbol_cache(PythonSymbolCache())

files = find_source_files(ctx)
parser = ctx.get_parser("python")
modules = [parser.parse_file(path, ctx) for path in files]
ctx.get_linker("python").link_files(modules, ctx)

result = ctx.get_resolver("python").resolve("acme_billing.invoice", "TaxRate", ctx)
print(result.status)  # resolved
for entity_id in result.resolved_ids:
    print(ctx.entity_registry.get(entity_id).fqn)  # acme_billing.tax.TaxRate
```

`result.status` is a `ResolutionStatus` (`RESOLVED`, `UNRESOLVED`, `AMBIGUOUS`, or
`INACCESSIBLE`) from `deproc.core.interfaces.resolver`. The result also carries
`unresolved_ids`, `ambiguous_ids`, `inaccessible_ids`, `reason` and `candidates`.

`PythonResolver` also provides `resolve_class_mro(class_id, ctx)` and
`get_inherited_members(class_id, ctx)`.

## Several roots

When several roots contribute the same package name, deproc follows Python's
import rule:

- A regular package (`__init__.py`) in one root wins over a same-named namespace
  portion in another root, in any root order. The shadowed container is removed
  and its modules stay indexed with no parent.
- Namespace portions with the same name in several roots become one namespace
  package.
- Two regular packages with the same name in different roots are both kept, and a
  warning names the roots, because Python would import whichever comes first on
  its path.

`PythonLinker.link_files()` applies this rule automatically when roots share one
registry; `PythonLinker(apply_package_precedence=False)` turns it off.
`deproc.plugins.python.utils.packages` provides
`apply_regular_package_precedence()` for separate per-root registries,
`apply_regular_package_precedence_to_registry()` for one shared registry, and
`find_regular_package_conflicts()`. Both precedence functions accept
`root_labels`, a mapping from source root id (`None` for a root without one) to
the text that names that root in the warning, such as its directory; roots
without a label are named by their id.

## Package layout

```
deproc-python/
├── deproc/plugins/python/
│   ├── parser/         PythonSourceParser (tree-sitter AST → entities)
│   ├── linker/         PythonLinker (modules → package hierarchy)
│   ├── resolver/       PythonResolver (names, MRO, inherited members)
│   ├── symbol_cache/   PythonSymbolCache (per-module cache)
│   └── utils/          imports, exports, MRO, package precedence, serialization
└── tests/
```

## Dependencies

- `deproc-core` (entity model, Context, EntityRegistry)
- `deproc-utils-tree-sitter` (AST walking utilities)
- `tree-sitter` (`>=0.25.2,<0.26`) and `tree-sitter-python` (Python grammar)
