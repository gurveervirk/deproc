"""Tests for Java linker."""

from deproc.core.context import Context
from deproc.core.runtime import EntityRegistry
from deproc.plugins.java.linker.main import JavaLinker
from deproc.plugins.java.linker.models import JavaPackage
from deproc.plugins.java.parser.models import JavaCompilationUnit


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
