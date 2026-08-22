"""Tests for Java symbol resolver."""

from deproc.core.context import Context
from deproc.core.interfaces.parser.models import SourceRange
from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.plugins.java.linker.models import JavaPackage
from deproc.plugins.java.parser.models import (
    JavaClass,
    JavaCompilationUnit,
    JavaImport,
    JavaModule,
)
from deproc.plugins.java.resolver.main import JavaResolver
from deproc.plugins.java.symbol_cache import JavaSymbolCache


def _sr() -> SourceRange:
    return SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=1)


def _make_cu(
    cu_fqn: str, package_fqn: str | None, imports: list[JavaImport], cu_id: str = "cu_1"
) -> JavaCompilationUnit:
    cu = JavaCompilationUnit(
        id=cu_id,
        fqn=cu_fqn,
        package_fqn=package_fqn,
        path=cu_fqn.replace(".", "/") + ".java",
        source="",
        docstring_range=None,
    )
    import_ids = []
    for imp in imports:
        import_ids.append(imp.id)
    cu.import_stmt_ids = import_ids
    return cu


def _make_class(fqn: str, class_id: str) -> JavaClass:
    return JavaClass(
        id=class_id,
        name=fqn.split(".")[-1],
        fqn=fqn,
        source_range=_sr(),
        docstring_range=None,
        visibility="public",
    )


def _make_package(fqn: str, package_id: str) -> JavaPackage:
    return JavaPackage(
        id=package_id,
        path=fqn.replace(".", "/"),
        fqn=fqn,
    )


def _make_module(
    module_name: str,
    module_id: str,
    package_fqns: list[str],
    cu_ids: list[str],
    requires: list[str] | None = None,
    requires_static: list[str] | None = None,
    requires_transitive: list[str] | None = None,
    exports: list[str] | None = None,
    qualified_exports: dict[str, list[str]] | None = None,
) -> JavaModule:
    return JavaModule(
        id=module_id,
        module_name=module_name,
        path=f"{module_name}/module-info.java",
        requires=requires or [],
        requires_static=requires_static or [],
        requires_transitive=requires_transitive or [],
        exports=exports or [],
        qualified_exports=qualified_exports or {},
        compilation_unit_ids=cu_ids,
        package_ids=[f"pkg_{p}" for p in package_fqns],
    )


def _context(
    cu: JavaCompilationUnit,
    classes: list[JavaClass] | None = None,
    imports: list[JavaImport] | None = None,
    use_cache: bool = False,
    packages: list[JavaPackage] | None = None,
    modules: list[JavaModule] | None = None,
) -> Context:
    ctx = Context()
    ctx.entity_registry = EntityRegistry()
    ctx._all_languages.add("java")
    ctx._selected_languages.add("java")
    if imports:
        for imp in imports:
            ctx.entity_registry.add(imp)
    if classes:
        for cls in classes:
            ctx.entity_registry.add(cls)
    if packages:
        for pkg in packages:
            ctx.entity_registry.add(pkg)
    if modules:
        for mod in modules:
            ctx.entity_registry.add(mod)
    ctx.entity_registry.add(cu)
    if use_cache:
        cache = JavaSymbolCache()
        ctx.set_symbol_cache(cache)
    return ctx


class TestResolveSingleType:
    def test_resolves_single_type_import(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.List",
            import_kind="single_type",
            imported_name="List",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        target = _make_class("java.util.List", "cls_1")
        ctx = _context(cu, [target], [imp])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "List", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.unresolved_ids == set()

    def test_symbol_not_found(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.List",
            import_kind="single_type",
            imported_name="List",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        ctx = _context(cu, [], [imp])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "List", ctx)
        assert result.resolved_ids == set()
        assert result.unresolved_ids == {"imp_1"}

    def test_non_matching_import_ignored(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.List",
            import_kind="single_type",
            imported_name="List",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        ctx = _context(cu, [], [imp])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "Map", ctx)
        assert result.resolved_ids == set()
        assert result.unresolved_ids == set()


class TestResolveOnDemand:
    def test_resolves_on_demand_import(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.*",
            import_kind="on_demand",
            imported_name=None,
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        target = _make_class("java.util.List", "cls_1")
        ctx = _context(cu, [target], [imp])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "List", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.unresolved_ids == set()

    def test_on_demand_not_found(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.*",
            import_kind="on_demand",
            imported_name=None,
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        ctx = _context(cu, [], [imp])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "List", ctx)
        assert result.resolved_ids == set()
        assert result.unresolved_ids == {"imp_1"}


class TestResolveStatic:
    def test_resolves_single_static_import(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.lang.Math.max",
            import_kind="single_static",
            imported_name="max",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        target = _make_class("java.lang.Math.max", "cls_1")
        ctx = _context(cu, [target], [imp])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "max", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.unresolved_ids == set()

    def test_resolves_static_on_demand_import(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.lang.Math.*",
            import_kind="static_on_demand",
            imported_name=None,
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        target = _make_class("java.lang.Math.max", "cls_1")
        ctx = _context(cu, [target], [imp])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "max", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.unresolved_ids == set()


class TestImplicitScopes:
    def test_same_package_visibility(self):
        cu = _make_cu("com.example.Foo", "com.example", [])
        target = _make_class("com.example.Bar", "cls_1")
        ctx = _context(cu, [target])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == {"cls_1"}

    def test_java_lang_auto_import(self):
        cu = _make_cu("com.example.Foo", "com.example", [])
        target = _make_class("java.lang.String", "cls_1")
        ctx = _context(cu, [target])
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "String", ctx)
        assert result.resolved_ids == {"cls_1"}

    def test_unnamed_package_lookup(self):
        cu = _make_cu("Foo", None, [])
        target = _make_class("Bar", "cls_1")
        ctx = _context(cu, [target])
        resolver = JavaResolver()
        result = resolver.resolve("Foo", "Bar", ctx)
        assert result.resolved_ids == {"cls_1"}

    def test_compilation_unit_not_found(self):
        ctx = Context()
        ctx.entity_registry = EntityRegistry()
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Missing", "List", ctx)
        assert result.resolved_ids == set()
        assert result.unresolved_ids == set()


class TestResolveCaching:
    def test_result_cached(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.List",
            import_kind="single_type",
            imported_name="List",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        target = _make_class("java.util.List", "cls_1")
        ctx = _context(cu, [target], [imp], use_cache=True)
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "List", ctx)
        assert result.resolved_ids == {"cls_1"}
        cache = ctx.get_symbol_cache("java")
        assert cache.get("com.example.Foo", "List") == ({"cls_1"}, set(), set())

    def test_cache_hit_returns_cached(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.List",
            import_kind="single_type",
            imported_name="List",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        target = _make_class("java.util.List", "cls_1")
        ctx = _context(cu, [target], [imp], use_cache=True)
        resolver = JavaResolver()
        result = resolver.resolve("com.example.Foo", "List", ctx)
        assert result.resolved_ids == {"cls_1"}

        ctx.entity_registry.remove("cls_1")
        cached_result = resolver.resolve("com.example.Foo", "List", ctx)
        assert cached_result.resolved_ids == {"cls_1"}


def _bar_import(import_id: str = "imp_bar") -> JavaImport:
    return JavaImport(
        id=import_id,
        import_path="modb.com.other.Bar",
        import_kind="single_type",
        imported_name="Bar",
        source_range=_sr(),
    )


class TestModuleVisibility:
    def test_same_module_visible(self):
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [], cu_id="cu_a_1")
        target = _make_class("moda.com.example.Bar", "cls_1")
        pkg = _make_package("moda.com.example", "pkg_moda.com.example")
        module = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
            exports=["moda.com.example"],
        )
        ctx = _context(cu, [target], packages=[pkg], modules=[module])
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.inaccessible_ids == set()

    def test_cross_module_requires_and_exports(self):
        imp = _bar_import()
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [imp], cu_id="cu_a_1")
        target = _make_class("modb.com.other.Bar", "cls_1")
        pkg_a = _make_package("moda.com.example", "pkg_moda.com.example")
        pkg_b = _make_package("modb.com.other", "pkg_modb.com.other")
        mod_a = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
            requires=["mod.b"],
        )
        mod_b = _make_module(
            "mod.b",
            "mod_b",
            package_fqns=["modb.com.other"],
            cu_ids=[],
            exports=["modb.com.other"],
        )
        ctx = _context(
            cu, [target], [imp], packages=[pkg_a, pkg_b], modules=[mod_a, mod_b]
        )
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.inaccessible_ids == set()

    def test_requires_but_not_exported(self):
        imp = _bar_import()
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [imp], cu_id="cu_a_1")
        target = _make_class("modb.com.other.Bar", "cls_1")
        pkg_a = _make_package("moda.com.example", "pkg_moda.com.example")
        pkg_b = _make_package("modb.com.other", "pkg_modb.com.other")
        mod_a = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
            requires=["mod.b"],
        )
        mod_b = _make_module(
            "mod.b",
            "mod_b",
            package_fqns=["modb.com.other"],
            cu_ids=[],
        )
        ctx = _context(
            cu, [target], [imp], packages=[pkg_a, pkg_b], modules=[mod_a, mod_b]
        )
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == set()
        assert result.inaccessible_ids == {"cls_1"}

    def test_exports_but_no_requires(self):
        imp = _bar_import()
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [imp], cu_id="cu_a_1")
        target = _make_class("modb.com.other.Bar", "cls_1")
        pkg_a = _make_package("moda.com.example", "pkg_moda.com.example")
        pkg_b = _make_package("modb.com.other", "pkg_modb.com.other")
        mod_a = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
        )
        mod_b = _make_module(
            "mod.b",
            "mod_b",
            package_fqns=["modb.com.other"],
            cu_ids=[],
            exports=["modb.com.other"],
        )
        ctx = _context(
            cu, [target], [imp], packages=[pkg_a, pkg_b], modules=[mod_a, mod_b]
        )
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == set()
        assert result.inaccessible_ids == {"cls_1"}

    def test_qualified_export_to_requester(self):
        imp = _bar_import()
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [imp], cu_id="cu_a_1")
        target = _make_class("modb.com.other.Bar", "cls_1")
        pkg_a = _make_package("moda.com.example", "pkg_moda.com.example")
        pkg_b = _make_package("modb.com.other", "pkg_modb.com.other")
        mod_a = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
            requires=["mod.b"],
        )
        mod_b = _make_module(
            "mod.b",
            "mod_b",
            package_fqns=["modb.com.other"],
            cu_ids=[],
            qualified_exports={"modb.com.other": ["mod.a"]},
        )
        ctx = _context(
            cu, [target], [imp], packages=[pkg_a, pkg_b], modules=[mod_a, mod_b]
        )
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.inaccessible_ids == set()

    def test_qualified_export_to_other_module_hidden(self):
        imp = _bar_import()
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [imp], cu_id="cu_a_1")
        target = _make_class("modb.com.other.Bar", "cls_1")
        pkg_a = _make_package("moda.com.example", "pkg_moda.com.example")
        pkg_b = _make_package("modb.com.other", "pkg_modb.com.other")
        mod_a = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
            requires=["mod.b"],
        )
        mod_b = _make_module(
            "mod.b",
            "mod_b",
            package_fqns=["modb.com.other"],
            cu_ids=[],
            qualified_exports={"modb.com.other": ["mod.c"]},
        )
        ctx = _context(
            cu, [target], [imp], packages=[pkg_a, pkg_b], modules=[mod_a, mod_b]
        )
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == set()
        assert result.inaccessible_ids == {"cls_1"}

    def test_requires_static_allows_compile_time(self):
        imp = _bar_import()
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [imp], cu_id="cu_a_1")
        target = _make_class("modb.com.other.Bar", "cls_1")
        pkg_a = _make_package("moda.com.example", "pkg_moda.com.example")
        pkg_b = _make_package("modb.com.other", "pkg_modb.com.other")
        mod_a = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
            requires_static=["mod.b"],
        )
        mod_b = _make_module(
            "mod.b",
            "mod_b",
            package_fqns=["modb.com.other"],
            cu_ids=[],
            exports=["modb.com.other"],
        )
        ctx = _context(
            cu, [target], [imp], packages=[pkg_a, pkg_b], modules=[mod_a, mod_b]
        )
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == {"cls_1"}

    def test_requires_transitive_closure(self):
        imp = _bar_import()
        cu = _make_cu("moda.com.example.Foo", "moda.com.example", [imp], cu_id="cu_a_1")
        target = _make_class("modb.com.other.Bar", "cls_1")
        pkg_a = _make_package("moda.com.example", "pkg_moda.com.example")
        pkg_b = _make_package("modb.com.other", "pkg_modb.com.other")
        mod_a = _make_module(
            "mod.a",
            "mod_a",
            package_fqns=["moda.com.example"],
            cu_ids=["cu_a_1"],
            requires_transitive=["mod.mid"],
        )
        mod_mid = _make_module(
            "mod.mid",
            "mod_mid",
            package_fqns=[],
            cu_ids=[],
            requires=["mod.b"],
        )
        mod_b = _make_module(
            "mod.b",
            "mod_b",
            package_fqns=["modb.com.other"],
            cu_ids=[],
            exports=["modb.com.other"],
        )
        ctx = _context(
            cu,
            [target],
            [imp],
            packages=[pkg_a, pkg_b],
            modules=[mod_a, mod_mid, mod_b],
        )
        result = JavaResolver().resolve("moda.com.example.Foo", "Bar", ctx)
        assert result.resolved_ids == {"cls_1"}
        assert result.inaccessible_ids == set()
