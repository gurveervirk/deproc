"""Tests for Java linker."""

from deproc.core.context import Context
from deproc.core.runtime import EntityRegistry
from deproc.plugins.java.linker.main import JavaLinker
from deproc.plugins.java.linker.models import JavaPackage
from deproc.plugins.java.parser.models import JavaCompilationUnit, JavaModule


def _make_context(base_path: str = "/src") -> Context:
    ctx = Context(base_path=base_path)
    ctx.entity_registry = EntityRegistry()
    return ctx


def _make_cu(fqn: str, package_fqn: str | None = None) -> JavaCompilationUnit:
    return JavaCompilationUnit(
        id=f"cu_{fqn}",
        fqn=fqn,
        package_fqn=package_fqn,
        path=fqn.replace(".", "/") + ".java",
        source="",
        docstring_range=None,
    )


class TestLinker:
    def test_create_package_model(self):
        pkg = JavaPackage(path="com/example", fqn="com.example")
        assert pkg.fqn == "com.example"
        assert pkg.subpackage_ids == []
        assert pkg.compilation_unit_ids == []

    def test_group_by_package(self):
        ctx = _make_context()
        cus = [
            _make_cu("com.example.foo.A", "com.example.foo"),
            _make_cu("com.example.foo.B", "com.example.foo"),
            _make_cu("com.example.bar.C", "com.example.bar"),
        ]
        linker = JavaLinker()
        linker.link_files(cus, ctx)

        foo_pkg = next(
            p
            for p in ctx.entity_registry.values()
            if isinstance(p, JavaPackage) and p.fqn == "com.example.foo"
        )
        bar_pkg = next(
            p
            for p in ctx.entity_registry.values()
            if isinstance(p, JavaPackage) and p.fqn == "com.example.bar"
        )
        assert len(foo_pkg.compilation_unit_ids) == 2
        assert len(bar_pkg.compilation_unit_ids) == 1

    def test_package_hierarchy(self):
        ctx = _make_context()
        cus = [_make_cu("com.example.foo.A", "com.example.foo")]
        linker = JavaLinker()
        linker.link_files(cus, ctx)

        pkgs = {
            p.fqn: p for p in ctx.entity_registry.values() if isinstance(p, JavaPackage)
        }
        assert "com" in pkgs
        assert "com.example" in pkgs
        assert "com.example.foo" in pkgs

        assert pkgs["com.example"].parent_id == pkgs["com"].id
        assert pkgs["com.example.foo"].parent_id == pkgs["com.example"].id
        assert pkgs["com.example"].id in pkgs["com"].subpackage_ids
        assert pkgs["com.example.foo"].id in pkgs["com.example"].subpackage_ids

    def test_unnamed_package_skipped(self):
        ctx = _make_context()
        cus = [_make_cu("MyClass", None)]
        linker = JavaLinker()
        top = linker.link_files(cus, ctx)
        assert top == []
        pkgs = [p for p in ctx.entity_registry.values() if isinstance(p, JavaPackage)]
        assert len(pkgs) == 0

    def test_top_level_returns_roots(self):
        ctx = _make_context()
        cus = [_make_cu("com.example.foo.A", "com.example.foo")]
        linker = JavaLinker()
        top = linker.link_files(cus, ctx)
        assert len(top) == 1
        assert top[0].fqn == "com"

    def test_multiple_roots(self):
        ctx = _make_context()
        cus = [
            _make_cu("com.example.foo.A", "com.example.foo"),
            _make_cu("org.other.B", "org.other"),
        ]
        linker = JavaLinker()
        top = linker.link_files(cus, ctx)
        assert {p.fqn for p in top} == {"com", "org"}

    def test_compilation_unit_attached(self):
        ctx = _make_context()
        cu = _make_cu("com.example.foo.A", "com.example.foo")
        linker = JavaLinker()
        linker.link_files([cu], ctx)
        foo_pkg = next(
            p
            for p in ctx.entity_registry.values()
            if isinstance(p, JavaPackage) and p.fqn == "com.example.foo"
        )
        assert cu.id in foo_pkg.compilation_unit_ids


def _make_module(module_name: str, path: str) -> JavaModule:
    return JavaModule(id=f"mod_{module_name}", module_name=module_name, path=path)


class TestModuleLinker:
    def test_module_assigned_root_dir_cus(self):
        ctx = _make_context()
        cu = _make_cu("com.example.foo.A", "com.example.foo")
        module = _make_module("com.example", "module-info.java")
        linker = JavaLinker()
        top = linker.link_files([cu, module], ctx)
        assert module in top
        assert cu.id in module.compilation_unit_ids

    def test_module_package_ids(self):
        ctx = _make_context()
        cu = _make_cu("com.example.foo.A", "com.example.foo")
        module = _make_module("com.example", "module-info.java")
        linker = JavaLinker()
        linker.link_files([cu, module], ctx)
        foo_pkg = next(
            p
            for p in ctx.entity_registry.values()
            if isinstance(p, JavaPackage) and p.fqn == "com.example.foo"
        )
        assert foo_pkg.id in module.package_ids

    def test_module_nested_root_excludes_outside_cus(self):
        ctx = _make_context()
        inside = _make_cu("com.example.foo.A", "com.example.foo")
        inside.path = "mod1/com/example/foo/A.java"
        outside = _make_cu("org.other.B", "org.other")
        module = _make_module("com.example", "mod1/module-info.java")
        linker = JavaLinker()
        linker.link_files([inside, outside, module], ctx)
        assert inside.id in module.compilation_unit_ids
        assert outside.id not in module.compilation_unit_ids

    def test_module_membership_is_directory_based(self):
        ctx = _make_context()
        a = _make_cu("com.example.A", "com.example")
        a.path = "mod1/com/example/A.java"
        different_pkg = _make_cu("com.example2.B", "com.example2")
        different_pkg.path = "mod1/com/example2/B.java"
        sibling = _make_cu("org.other.C", "org.other")
        sibling.path = "mod10/org/other/C.java"
        module = _make_module("com.example", "mod1/module-info.java")
        linker = JavaLinker()
        linker.link_files([a, different_pkg, sibling, module], ctx)
        assert a.id in module.compilation_unit_ids
        assert different_pkg.id in module.compilation_unit_ids
        assert sibling.id not in module.compilation_unit_ids

    def test_no_module_returns_packages_only(self):
        ctx = _make_context()
        cu = _make_cu("com.example.foo.A", "com.example.foo")
        linker = JavaLinker()
        top = linker.link_files([cu], ctx)
        assert len(top) == 1
        assert isinstance(top[0], JavaPackage)
