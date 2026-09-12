"""Tests for Java symbol resolver."""

from deproc.core.context import Context
from deproc.core.interfaces.parser.models import SourceRange
from deproc.core.interfaces.resolver import ResolutionStatus
from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.plugins.java.linker.models import JavaPackage
from deproc.plugins.java.parser.models import (
    JavaClass,
    JavaCompilationUnit,
    JavaImport,
    JavaInterface,
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


def _make_class(fqn: str, class_id: str, visibility: str = "public") -> JavaClass:
    return JavaClass(
        id=class_id,
        name=fqn.split(".")[-1],
        fqn=fqn,
        source_range=_sr(),
        docstring_range=None,
        visibility=visibility,
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

    def test_conflicting_on_demand_imports_are_ambiguous_for_qualified_member_type(
        self,
    ):
        imports = [
            JavaImport(
                id="imp_1",
                import_path="com.first.*",
                import_kind="on_demand",
                source_range=_sr(),
            ),
            JavaImport(
                id="imp_2",
                import_path="com.second.*",
                import_kind="on_demand",
                source_range=_sr(),
            ),
        ]
        cu = _make_cu("com.example.Foo", "com.example", imports)
        first_outer = _make_class("com.first.Outer", "first_outer")
        first_inner = _make_class("com.first.Outer.Inner", "first_inner")
        first_inner.parent_id = first_outer.id
        second_outer = _make_class("com.second.Outer", "second_outer")
        second_inner = _make_class("com.second.Outer.Inner", "second_inner")
        second_inner.parent_id = second_outer.id
        owner = _make_class("com.example.Foo", "owner")
        owner.parent_id = cu.id
        ctx = _context(
            cu,
            [first_outer, first_inner, second_outer, second_inner, owner],
            imports,
        )

        result = JavaResolver().resolve_type_reference("Outer.Inner", owner, ctx)

        assert result.status is ResolutionStatus.AMBIGUOUS
        assert result.candidates == ("first_inner", "second_inner")

    def test_ambiguous_leading_type_is_not_disambiguated_by_member_type(self):
        imports = [
            JavaImport(
                id="imp_1",
                import_path="com.first.*",
                import_kind="on_demand",
                source_range=_sr(),
            ),
            JavaImport(
                id="imp_2",
                import_path="com.second.*",
                import_kind="on_demand",
                source_range=_sr(),
            ),
        ]
        cu = _make_cu("com.example.Foo", "com.example", imports)
        first_outer = _make_class("com.first.Outer", "first_outer")
        first_inner = _make_class("com.first.Outer.Inner", "first_inner")
        first_inner.parent_id = first_outer.id
        second_outer = _make_class("com.second.Outer", "second_outer")
        owner = _make_class("com.example.Foo", "owner")
        owner.parent_id = cu.id
        ctx = _context(
            cu,
            [first_outer, first_inner, second_outer, owner],
            imports,
        )

        result = JavaResolver().resolve_type_reference("Outer.Inner", owner, ctx)

        assert result.status is ResolutionStatus.AMBIGUOUS
        assert result.value is None

    def test_imported_leading_type_shadows_package_qualified_name(self):
        imp = JavaImport(
            id="imp_1",
            import_path="p.Outer",
            import_kind="single_type",
            imported_name="Outer",
            source_range=_sr(),
        )
        cu = _make_cu("q.Use", "q", [imp])
        owner = _make_class("q.Use", "owner")
        owner.parent_id = cu.id
        imported_cu = _make_cu("p.Outer", "p", [], cu_id="cu_imported")
        imported_outer = _make_class("p.Outer", "imported_outer")
        imported_outer.parent_id = imported_cu.id
        imported_inner = _make_class("p.Outer.Inner", "imported_inner")
        imported_inner.parent_id = imported_outer.id
        package_cu = _make_cu("Outer.Inner", "Outer", [], cu_id="cu_package")
        package_inner = _make_class("Outer.Inner", "package_inner")
        package_inner.parent_id = package_cu.id
        ctx = _context(
            cu,
            [owner, imported_outer, imported_inner, package_inner],
            [imp],
        )
        ctx.entity_registry.add(imported_cu)
        ctx.entity_registry.add(package_cu)

        result = JavaResolver().resolve_type_reference("Outer.Inner", owner, ctx)
        direct_result = JavaResolver().resolve_type_reference(
            "p.Outer.Inner", owner, ctx
        )

        assert result.status is ResolutionStatus.RESOLVED
        assert result.value == "imported_inner"
        assert direct_result.status is ResolutionStatus.RESOLVED
        assert direct_result.value == "imported_inner"


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

    def test_same_package_type_shadows_on_demand_import(self):
        imp = JavaImport(
            id="imp_1",
            import_path="com.other.*",
            import_kind="on_demand",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        same_package = _make_class("com.example.Base", "same")
        imported = _make_class("com.other.Base", "imported")
        owner = _make_class("com.example.Foo", "owner")
        owner.parent_id = cu.id
        ctx = _context(cu, [same_package, imported, owner], [imp])
        resolver = JavaResolver()

        reference = resolver.resolve_type_reference("Base", owner, ctx)
        symbol = resolver.resolve("com.example.Foo", "Base", ctx)

        assert reference.status is ResolutionStatus.RESOLVED
        assert reference.value == "same"
        assert symbol.resolved_ids == {"same"}

    def test_single_type_import_shadows_same_package_type(self):
        imp = JavaImport(
            id="imp_1",
            import_path="com.other.Base",
            import_kind="single_type",
            imported_name="Base",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        same_package = _make_class("com.example.Base", "same")
        imported = _make_class("com.other.Base", "imported")
        owner = _make_class("com.example.Foo", "owner")
        owner.parent_id = cu.id
        ctx = _context(cu, [same_package, imported, owner], [imp])
        result = JavaResolver().resolve_type_reference("Base", owner, ctx)

        assert result.status is ResolutionStatus.RESOLVED
        assert result.value == "imported"

    def test_conflicting_on_demand_imports_are_ambiguous(self):
        imports = [
            JavaImport(
                id="imp_1",
                import_path="com.first.*",
                import_kind="on_demand",
                source_range=_sr(),
            ),
            JavaImport(
                id="imp_2",
                import_path="com.second.*",
                import_kind="on_demand",
                source_range=_sr(),
            ),
        ]
        cu = _make_cu("com.example.Foo", "com.example", imports)
        first = _make_class("com.first.Base", "first")
        second = _make_class("com.second.Base", "second")
        owner = _make_class("com.example.Foo", "owner")
        owner.parent_id = cu.id
        ctx = _context(cu, [first, second, owner], imports)
        result = JavaResolver().resolve_type_reference("Base", owner, ctx)

        assert result.status is ResolutionStatus.AMBIGUOUS
        assert result.candidates == ("first", "second")

    def test_package_private_type_is_inaccessible_across_packages(self):
        imp = JavaImport(
            id="imp_1",
            import_path="com.other.Hidden",
            import_kind="single_type",
            imported_name="Hidden",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Foo", "com.example", [imp])
        hidden = _make_class("com.other.Hidden", "hidden", visibility="package-private")
        owner = _make_class("com.example.Foo", "owner")
        owner.parent_id = cu.id
        ctx = _context(cu, [hidden, owner], [imp])
        result = JavaResolver().resolve_type_reference("Hidden", owner, ctx)

        assert result.status is ResolutionStatus.INACCESSIBLE
        assert result.candidates == ("hidden",)

    def test_package_private_type_is_visible_in_same_package(self):
        cu = _make_cu("com.example.Foo", "com.example", [])
        hidden = _make_class(
            "com.example.Hidden", "hidden", visibility="package-private"
        )
        owner = _make_class("com.example.Foo", "owner")
        owner.parent_id = cu.id
        ctx = _context(cu, [hidden, owner])
        result = JavaResolver().resolve_type_reference("Hidden", owner, ctx)

        assert result.status is ResolutionStatus.RESOLVED
        assert result.value == "hidden"

    def test_nested_type_shadows_imported_type(self):
        imp = JavaImport(
            id="imp_1",
            import_path="com.other.Inner",
            import_kind="single_type",
            imported_name="Inner",
            source_range=_sr(),
        )
        cu = _make_cu("com.example.Outer", "com.example", [imp])
        outer = _make_class("com.example.Outer", "outer")
        outer.parent_id = cu.id
        nested = _make_class("com.example.Outer.Inner", "nested")
        nested.parent_id = outer.id
        imported = _make_class("com.other.Inner", "imported")
        ctx = _context(cu, [outer, nested, imported], [imp])

        result = JavaResolver().resolve_type_reference("Inner", outer, ctx)

        assert result.status is ResolutionStatus.RESOLVED
        assert result.value == "nested"

    def test_private_member_type_is_visible_to_sibling_nested_type(self):
        cu = _make_cu("com.example.Client", "com.example", [])
        outer = _make_class("com.example.Outer", "outer")
        outer.parent_id = cu.id
        secret = _make_class("com.example.Outer.Secret", "secret", "private")
        secret.parent_id = outer.id
        sibling = _make_class("com.example.Outer.Sibling", "sibling")
        sibling.parent_id = outer.id
        ctx = _context(cu, [outer, secret, sibling])

        result = JavaResolver().resolve_type_reference("Secret", sibling, ctx)

        assert result.status is ResolutionStatus.RESOLVED
        assert result.value == "secret"

    def test_interface_member_type_is_effectively_public(self):
        owner_cu = _make_cu("com.client.Client", "com.client", [])
        api_cu = _make_cu("com.api.Api", "com.api", [], cu_id="cu_api")
        api = JavaInterface(
            id="api",
            name="Api",
            fqn="com.api.Api",
            parent_id=api_cu.id,
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
        )
        nested = _make_class("com.api.Api.Nested", "nested", "package-private")
        nested.parent_id = api.id
        client = _make_class("com.client.Client", "client")
        client.parent_id = owner_cu.id
        ctx = _context(owner_cu, [api, nested, client])
        ctx.entity_registry.add(api_cu)

        result = JavaResolver().resolve_type_reference(
            "com.api.Api.Nested", client, ctx
        )

        assert result.status is ResolutionStatus.RESOLVED
        assert result.value == "nested"

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


class TestTypeRelationships:
    def test_resolves_superclass_property(self):
        cu = _make_cu("pkg.Child", "pkg", [], cu_id="cu_child")
        base = _make_class("pkg.Base", "base")
        child = _make_class("pkg.Child", "child")
        child.parent_id = cu.id
        child.superclass = "pkg.Base"
        ctx = _context(cu, [base, child])

        result = JavaResolver().resolve_type_reference(child.superclass, child, ctx)

        assert result.status is ResolutionStatus.RESOLVED
        assert result.value == base.id

    def test_reports_ambiguous_superclass_property(self):
        cu = _make_cu("pkg.Child", "pkg", [], cu_id="cu_child")
        child = _make_class("pkg.Child", "child")
        child.parent_id = cu.id
        child.superclass = "pkg.Base"
        first = _make_class("pkg.Base", "base_1")
        second = _make_class("pkg.Base", "base_2")
        ctx = _context(cu, [child, first, second])

        result = JavaResolver().resolve_type_reference(child.superclass, child, ctx)

        assert result.status is ResolutionStatus.AMBIGUOUS
        assert result.candidates == (first.id, second.id)

    def test_reports_unresolved_superclass_property(self):
        cu = _make_cu("pkg.Child", "pkg", [], cu_id="cu_child")
        child = _make_class("pkg.Child", "child")
        child.parent_id = cu.id
        child.superclass = "pkg.Missing"
        ctx = _context(cu, [child])

        result = JavaResolver().resolve_type_reference(child.superclass, child, ctx)

        assert result.status is ResolutionStatus.UNRESOLVED

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
