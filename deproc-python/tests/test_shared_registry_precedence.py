import itertools
import logging
from pathlib import Path

import pytest
from deproc.core.context import Context
from deproc.core.runtime import EntityRegistry
from deproc.plugins.python.linker.main import PythonLinker
from deproc.plugins.python.linker.models import PythonNamespacePackage, PythonPackage
from deproc.plugins.python.parser.main import PythonSourceParser
from deproc.plugins.python.parser.models import PythonModule
from deproc.plugins.python.utils.packages import apply_regular_package_precedence

PACKAGES_LOGGER = "deproc.plugins.python.utils.packages"

Layout = dict[str, dict[str, str]]

REGULAR_AND_NAMESPACE: Layout = {
    "core": {"acme/__init__.py": "", "acme/a.py": "class A: pass\n"},
    "plugins": {"acme/billing.py": "class B: pass\n"},
}
NESTED_NAMESPACE: Layout = {
    "core": {"acme/__init__.py": "", "acme/sub/x.py": "class X: pass\n"},
    "plugins": {"acme/sub/y.py": "class Y: pass\n"},
}
NAMESPACE_ONLY: Layout = {
    "core": {"acme/a.py": "class A: pass\n"},
    "plugins": {"acme/b.py": "class B: pass\n"},
}
THREE_ROOTS: Layout = {
    "r1": {"acme/one.py": "class One: pass\n"},
    "r2": {"acme/__init__.py": "", "acme/two.py": "class Two: pass\n"},
    "r3": {"acme/three.py": "class Three: pass\n"},
}
TWO_REGULAR: Layout = {
    "first": {"acme/__init__.py": "", "acme/one.py": "class One: pass\n"},
    "second": {"acme/__init__.py": "", "acme/two.py": "class Two: pass\n"},
}
LAYOUTS = {
    "regular-and-namespace": REGULAR_AND_NAMESPACE,
    "nested-namespace": NESTED_NAMESPACE,
    "namespace-only": NAMESPACE_ONLY,
    "three-roots": THREE_ROOTS,
}


def _write(base: Path, files: dict[str, str]) -> None:
    for relative_path, source in files.items():
        path = base / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


def _link_into(
    registry: EntityRegistry,
    base: Path,
    name: str,
    files: dict[str, str],
    root_id: str | None,
    linker: PythonLinker | None = None,
) -> list:
    _write(base / name, files)
    context = Context(base_path=str(base / name))
    context.source_root_id = root_id
    context.entity_registry = registry
    modules = [
        PythonSourceParser().parse_file(str(base / name / relative_path), context)
        for relative_path in sorted(files)
    ]
    return (linker or PythonLinker()).link_files(modules, context)


def _link_shared(
    base: Path, layout: Layout, order: tuple[str, ...], root_ids: bool = True
) -> EntityRegistry:
    registry = EntityRegistry()
    for name in order:
        _link_into(registry, base, name, layout[name], name if root_ids else None)
    return registry


def _link_per_root(
    base: Path, layout: Layout, order: tuple[str, ...]
) -> EntityRegistry:
    registries = []
    for name in order:
        registry = EntityRegistry()
        _link_into(registry, base, name, layout[name], name)
        registries.append(registry)
    apply_regular_package_precedence(registries)
    merged = EntityRegistry()
    for registry in registries:
        merged.merge_from(registry)
    return merged


def _fqn_of(registry: EntityRegistry, entity_id: str | None) -> str | None:
    entity = registry.get(entity_id) if entity_id else None
    return getattr(entity, "fqn", None)


def _summary(registry: EntityRegistry) -> list[tuple]:
    rows = []
    for entity in registry.values():
        if isinstance(entity, (PythonPackage, PythonNamespacePackage)):
            children = tuple(
                sorted(
                    f"{type(registry.get(child)).__name__}:{_fqn_of(registry, child)}"
                    for child in entity.submodule_ids
                )
            )
            parent = registry.get(entity.parent_id) if entity.parent_id else None
            parent_label = (
                f"{type(parent).__name__}:{parent.fqn}" if parent is not None else None
            )
            rows.append((type(entity).__name__, entity.fqn, children, parent_label))
        elif isinstance(entity, PythonModule):
            parent = registry.get(entity.parent_id) if entity.parent_id else None
            parent_label = (
                f"{type(parent).__name__}:{parent.fqn}" if parent is not None else None
            )
            rows.append((type(entity).__name__, entity.fqn, (), parent_label))
    return sorted(rows, key=str)


def _module(registry: EntityRegistry, fqn: str) -> PythonModule:
    (entity_id,) = registry.get_ids_by_fqn(fqn)
    entity = registry.get(entity_id)
    assert isinstance(entity, PythonModule)
    return entity


def _containers(registry: EntityRegistry, fqn: str) -> list:
    return [
        entity
        for entity in registry.values()
        if isinstance(entity, PythonNamespacePackage) and entity.fqn == fqn
    ]


@pytest.mark.parametrize("order", [("core", "plugins"), ("plugins", "core")])
def test_shared_registry_drops_namespace_portion_shadowed_by_a_regular_package(
    tmp_path, order
):
    registry = _link_shared(tmp_path, REGULAR_AND_NAMESPACE, order)

    assert _containers(registry, "acme") == []
    (package_id,) = registry.get_ids_by_fqn("acme")
    package = registry.get(package_id)
    assert isinstance(package, PythonPackage)
    assert package.submodule_ids == [_module(registry, "acme.a").id]
    assert _module(registry, "acme.a").parent_id == package.id
    assert _module(registry, "acme.billing").parent_id is None


@pytest.mark.parametrize("order", [("core", "plugins"), ("plugins", "core")])
def test_shared_registry_keeps_modules_of_the_regular_root_in_nested_namespaces(
    tmp_path, order
):
    registry = _link_shared(tmp_path, NESTED_NAMESPACE, order)

    (package_id,) = registry.get_ids_by_fqn("acme")
    package = registry.get(package_id)
    assert isinstance(package, PythonPackage)
    (sub,) = _containers(registry, "acme.sub")
    assert sub.parent_id == package.id
    assert sub.submodule_ids == [_module(registry, "acme.sub.x").id]
    assert _module(registry, "acme.sub.y").parent_id is None
    assert _containers(registry, "acme") == []


@pytest.mark.parametrize("name", sorted(LAYOUTS))
def test_shared_registry_matches_per_root_linking_in_every_root_order(tmp_path, name):
    layout = LAYOUTS[name]
    for index, order in enumerate(itertools.permutations(layout)):
        shared = _link_shared(tmp_path / f"shared-{index}", layout, order)
        per_root = _link_per_root(tmp_path / f"per-root-{index}", layout, order)

        assert _summary(shared) == _summary(per_root), order


def test_shared_registry_leaves_namespace_portions_without_a_regular_package(
    tmp_path,
):
    registry = _link_shared(tmp_path, NAMESPACE_ONLY, ("core", "plugins"))

    (namespace,) = _containers(registry, "acme")
    assert sorted(namespace.submodule_ids) == sorted(
        [_module(registry, "acme.a").id, _module(registry, "acme.b").id]
    )
    assert _module(registry, "acme.a").parent_id == namespace.id
    assert _module(registry, "acme.b").parent_id == namespace.id


def test_shared_registry_without_root_ids_still_drops_a_same_named_portion(tmp_path):
    registry = _link_shared(
        tmp_path, REGULAR_AND_NAMESPACE, ("core", "plugins"), root_ids=False
    )

    assert _containers(registry, "acme") == []
    assert _module(registry, "acme.billing").parent_id is None


def test_shared_registry_without_root_ids_cannot_tell_nested_portions_apart(tmp_path):
    registry = _link_shared(
        tmp_path, NESTED_NAMESPACE, ("core", "plugins"), root_ids=False
    )

    (sub,) = _containers(registry, "acme.sub")
    assert _module(registry, "acme.sub.y").parent_id == sub.id


def test_link_files_returns_only_containers_that_survive_precedence(tmp_path):
    registry = EntityRegistry()
    _link_into(registry, tmp_path, "core", REGULAR_AND_NAMESPACE["core"], "core")

    returned = _link_into(
        registry, tmp_path, "plugins", REGULAR_AND_NAMESPACE["plugins"], "plugins"
    )

    assert all(entity.id in registry for entity in returned)
    assert not any(isinstance(entity, PythonNamespacePackage) for entity in returned)


def test_precedence_function_for_one_registry_reports_and_is_idempotent(tmp_path):
    from deproc.plugins.python.utils.packages import (
        apply_regular_package_precedence_to_registry,
    )

    merged = EntityRegistry()
    for name, files in REGULAR_AND_NAMESPACE.items():
        registry = EntityRegistry()
        _link_into(registry, tmp_path, name, files, name)
        merged.merge_from(registry)
    assert len(_containers(merged, "acme")) == 1

    shadowed = apply_regular_package_precedence_to_registry(merged)

    assert [portion.fqn for portion in shadowed] == ["acme"]
    assert shadowed[0].detached_ids == (_module(merged, "acme.billing").id,)
    assert _containers(merged, "acme") == []
    assert apply_regular_package_precedence_to_registry(merged) == []


def test_two_same_named_regular_packages_are_both_kept_and_a_warning_is_logged(
    tmp_path, caplog
):
    with caplog.at_level(logging.WARNING, logger=PACKAGES_LOGGER):
        registry = _link_shared(tmp_path, TWO_REGULAR, ("first", "second"))

    packages = [
        entity
        for entity in registry.values()
        if isinstance(entity, PythonPackage) and entity.fqn == "acme"
    ]
    assert len(packages) == 2
    assert _module(registry, "acme.one").parent_id in {p.id for p in packages}
    assert _module(registry, "acme.two").parent_id in {p.id for p in packages}
    messages = [r.getMessage() for r in caplog.records if r.name == PACKAGES_LOGGER]
    assert any(
        "regular package 'acme'" in m and "first" in m and "second" in m
        for m in messages
    ), messages


def test_per_root_registries_with_same_named_regular_packages_log_a_warning(
    tmp_path, caplog
):
    registries = []
    for name, files in TWO_REGULAR.items():
        registry = EntityRegistry()
        _link_into(registry, tmp_path, name, files, name)
        registries.append(registry)

    with caplog.at_level(logging.WARNING, logger=PACKAGES_LOGGER):
        shadowed = apply_regular_package_precedence(registries)

    assert shadowed == []
    messages = [r.getMessage() for r in caplog.records if r.name == PACKAGES_LOGGER]
    assert any("regular package 'acme'" in m for m in messages), messages


def test_find_regular_package_conflicts_lists_each_name_with_its_roots(tmp_path):
    from deproc.plugins.python.utils.packages import (
        RegularPackageConflict,
        find_regular_package_conflicts,
    )

    registries = []
    for name, files in TWO_REGULAR.items():
        registry = EntityRegistry()
        _link_into(registry, tmp_path, name, files, name)
        registries.append(registry)

    assert find_regular_package_conflicts(registries) == [
        RegularPackageConflict(fqn="acme", source_root_ids=("first", "second"))
    ]


def test_find_regular_package_conflicts_ignores_a_single_regular_package(tmp_path):
    from deproc.plugins.python.utils.packages import find_regular_package_conflicts

    registry = _link_shared(tmp_path, REGULAR_AND_NAMESPACE, ("core", "plugins"))

    assert find_regular_package_conflicts([registry]) == []


def test_no_warning_when_a_regular_package_only_shadows_a_namespace_portion(
    tmp_path, caplog
):
    with caplog.at_level(logging.WARNING, logger=PACKAGES_LOGGER):
        _link_shared(tmp_path, REGULAR_AND_NAMESPACE, ("core", "plugins"))

    assert not any(
        "defined in more than one root" in r.getMessage() for r in caplog.records
    )


@pytest.mark.parametrize("root_id", ["core", None])
def test_single_root_regular_package_tree_is_left_untouched(tmp_path, caplog, root_id):
    from deproc.plugins.python.utils.packages import (
        apply_regular_package_precedence_to_registry,
    )

    (tmp_path / "core" / "acme" / ".hidden").mkdir(parents=True)
    registry = EntityRegistry()

    with caplog.at_level(logging.WARNING, logger=PACKAGES_LOGGER):
        _link_into(
            registry,
            tmp_path,
            "core",
            {
                "acme/__init__.py": "",
                "acme/a.py": "class A: pass\n",
                "acme/sub/x.py": "class X: pass\n",
            },
            root_id,
        )

    (hidden,) = _containers(registry, "acme..hidden")
    assert hidden.submodule_ids == []
    (sub,) = _containers(registry, "acme.sub")
    assert sub.submodule_ids == [_module(registry, "acme.sub.x").id]
    (package_id,) = registry.get_ids_by_fqn("acme")
    package = registry.get(package_id)
    assert isinstance(package, PythonPackage)
    assert {hidden.parent_id, sub.parent_id} == {package.id}
    assert [r for r in caplog.records if r.name == PACKAGES_LOGGER] == []
    assert apply_regular_package_precedence_to_registry(registry) == []


def test_linker_can_skip_package_precedence(tmp_path, caplog):
    from deproc.plugins.python.utils.packages import (
        apply_regular_package_precedence_to_registry,
    )

    registry = EntityRegistry()
    linker = PythonLinker(apply_package_precedence=False)

    with caplog.at_level(logging.WARNING, logger=PACKAGES_LOGGER):
        for name in ("core", "plugins"):
            _link_into(
                registry, tmp_path, name, REGULAR_AND_NAMESPACE[name], name, linker
            )

    (container,) = _containers(registry, "acme")
    assert _module(registry, "acme.billing").parent_id == container.id
    assert [r for r in caplog.records if r.name == PACKAGES_LOGGER] == []

    shadowed = apply_regular_package_precedence_to_registry(registry)

    assert [portion.fqn for portion in shadowed] == ["acme"]
    assert _containers(registry, "acme") == []


def test_linker_skipping_precedence_logs_no_conflict_warning(tmp_path, caplog):
    registry = EntityRegistry()
    linker = PythonLinker(apply_package_precedence=False)

    with caplog.at_level(logging.WARNING, logger=PACKAGES_LOGGER):
        for name in ("first", "second"):
            _link_into(registry, tmp_path, name, TWO_REGULAR[name], name, linker)

    assert [r for r in caplog.records if r.name == PACKAGES_LOGGER] == []


def test_linker_applies_package_precedence_by_default():
    assert PythonLinker().apply_package_precedence is True
    assert (
        PythonLinker(apply_package_precedence=False).apply_package_precedence is False
    )
