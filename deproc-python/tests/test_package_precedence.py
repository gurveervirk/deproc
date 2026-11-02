from pathlib import Path

from deproc.core.context import Context
from deproc.core.runtime import EntityRegistry
from deproc.plugins.python.linker.main import PythonLinker
from deproc.plugins.python.linker.models import PythonNamespacePackage, PythonPackage
from deproc.plugins.python.parser.main import PythonSourceParser
from deproc.plugins.python.parser.models import PythonModule
from deproc.plugins.python.utils.packages import apply_regular_package_precedence


def _link_root(tmp_path: Path, name: str, files: dict[str, str]) -> EntityRegistry:
    root = tmp_path / name
    for relative_path, source in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    context = Context(base_path=str(root))
    context.source_root_id = name
    context.entity_registry = EntityRegistry()
    modules = [
        PythonSourceParser().parse_file(str(root / relative_path), context)
        for relative_path in sorted(files)
    ]
    PythonLinker().link_files(modules, context)
    return context.entity_registry


def _module(registry: EntityRegistry, fqn: str) -> PythonModule:
    (entity_id,) = registry.get_ids_by_fqn(fqn)
    entity = registry.get(entity_id)
    assert isinstance(entity, PythonModule)
    return entity


REGULAR = {"ns/__init__.py": "", "ns/a.py": "class A: pass\n"}
NAMESPACE = {"ns/b.py": "class B: pass\n"}


def test_regular_package_wins_over_namespace_portion_in_either_order(tmp_path):
    for order in ("regular-first", "namespace-first"):
        regular = _link_root(tmp_path / order, "regular", REGULAR)
        namespace = _link_root(tmp_path / order, "namespace", NAMESPACE)
        registries = (
            [regular, namespace] if order == "regular-first" else [namespace, regular]
        )

        shadowed = apply_regular_package_precedence(registries)

        assert [portion.fqn for portion in shadowed] == ["ns"]
        assert not any(
            isinstance(entity, PythonNamespacePackage)
            for registry in registries
            for entity in registry.values()
        )
        assert _module(namespace, "ns.b").parent_id is None
        assert shadowed[0].detached_ids == (_module(namespace, "ns.b").id,)
        regular_package = next(
            entity for entity in regular.values() if isinstance(entity, PythonPackage)
        )
        assert _module(regular, "ns.a").parent_id == regular_package.id


def test_shadowed_portion_is_removed_before_the_registries_are_merged(tmp_path):
    regular = _link_root(tmp_path, "regular", REGULAR)
    namespace = _link_root(tmp_path, "namespace", NAMESPACE)

    apply_regular_package_precedence([regular, namespace])
    merged = EntityRegistry()
    merged.merge_from(regular)
    merged.merge_from(namespace)

    assert len(merged.get_ids_by_fqn("ns")) == 1
    (package,) = [merged.get(entity_id) for entity_id in merged.get_ids_by_fqn("ns")]
    assert isinstance(package, PythonPackage)
    assert package.submodule_ids == [_module(regular, "ns.a").id]
    assert _module(merged, "ns.b").parent_id is None


def test_namespace_portions_without_a_regular_package_are_left_alone(tmp_path):
    first = _link_root(tmp_path, "first", {"ns/a.py": "class A: pass\n"})
    second = _link_root(tmp_path, "second", NAMESPACE)

    assert apply_regular_package_precedence([first, second]) == []

    merged = EntityRegistry()
    merged.merge_from(first)
    merged.merge_from(second)
    (namespace,) = [merged.get(entity_id) for entity_id in merged.get_ids_by_fqn("ns")]
    assert isinstance(namespace, PythonNamespacePackage)
    assert len(namespace.submodule_ids) == 2


def test_namespace_subpackage_inside_the_regular_root_is_kept(tmp_path):
    regular = _link_root(
        tmp_path,
        "regular",
        {"ns/__init__.py": "", "ns/sub/x.py": "class X: pass\n"},
    )
    namespace = _link_root(tmp_path, "namespace", {"ns/sub/y.py": "class Y: pass\n"})

    shadowed = apply_regular_package_precedence([regular, namespace])

    assert [portion.fqn for portion in shadowed] == ["ns"]
    assert shadowed[0].registry_index == 1
    assert shadowed[0].detached_ids == (_module(namespace, "ns.sub.y").id,)
    assert not any(
        isinstance(entity, PythonNamespacePackage) for entity in namespace.values()
    )
    kept = [
        entity
        for entity in regular.values()
        if isinstance(entity, PythonNamespacePackage)
    ]
    assert [entity.fqn for entity in kept] == ["ns.sub"]
    regular_package = next(
        entity for entity in regular.values() if isinstance(entity, PythonPackage)
    )
    assert kept[0].parent_id == regular_package.id
    assert kept[0].submodule_ids == [_module(regular, "ns.sub.x").id]
    assert _module(namespace, "ns.sub.y").parent_id is None


def test_registries_without_foreign_regular_packages_are_untouched(tmp_path):
    only = _link_root(tmp_path, "only", {**REGULAR, "other/m.py": "x = 1\n"})
    before = {entity.id: entity.parent_id for entity in only.values()}

    assert apply_regular_package_precedence([only]) == []

    assert {entity.id: entity.parent_id for entity in only.values()} == before
