from deproc.core.context import Context
from deproc.core.interfaces.parser.models import SourceRange
from deproc.core.interfaces.resolver import ResolutionStatus
from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.plugins.python.parser.models import (
    PythonClass,
    PythonImportStatement,
    PythonModule,
)
from deproc.plugins.python.resolver.main import PythonResolver
from deproc.plugins.python.utils.exports import (
    build_module_exports,
    get_dynamic_export_modules,
)


def _make_module(fqn, all_exports=None):
    m = PythonModule(
        fqn=fqn,
        path=f"{fqn.replace('.', '/')}.py",
        docstring_range=None,
        source="# placeholder",
    )
    m.all_exports = all_exports
    return m


class TestBuildModuleExports:
    def test_with_all_exports(self):
        reg = EntityRegistry()
        m = _make_module("pkg.mod", ["foo", "bar"])
        reg.add(m)
        result = build_module_exports(reg)
        assert result == {"pkg.mod": {"foo", "bar"}}

    def test_without_all_exports(self):
        reg = EntityRegistry()
        m = _make_module("pkg.mod")
        reg.add(m)
        result = build_module_exports(reg)
        assert result == {}

    def test_with_empty_all_exports(self):
        reg = EntityRegistry()
        m = _make_module("pkg.mod", [])
        reg.add(m)
        result = build_module_exports(reg)
        assert result == {"pkg.mod": set()}

    def test_ignores_non_module_entities(self):
        reg = EntityRegistry()
        func = PythonModule(
            fqn="pkg.func", path="pkg/func.py", docstring_range=None, source="# x"
        )
        reg.add(func)
        result = build_module_exports(reg)
        assert result == {}

    def test_includes_direct_public_entities(self):
        reg = EntityRegistry()
        module = _make_module("pkg.mod")
        entity = PythonClass(
            id="class",
            parent_id=module.id,
            name="Visible",
            fqn="pkg.mod.Visible",
            source_range=SourceRange(
                lineno=1, end_lineno=1, col_offset=0, end_col_offset=15
            ),
            docstring_range=None,
            visibility="public",
        )
        module.type_ids = [entity.id]
        reg.add_all([module, entity])

        assert build_module_exports(reg) == {"pkg.mod": {"Visible"}}

    def test_wildcard_reexports_are_transitive(self):
        reg = EntityRegistry()
        base = _make_module("pkg.base", ["Visible"])
        facade = _make_module("pkg.facade")
        import_stmt = PythonImportStatement(
            id="import",
            parent_id=facade.id,
            path="pkg.base",
            type="from_import",
            source_range=SourceRange(
                lineno=1, end_lineno=1, col_offset=0, end_col_offset=20
            ),
            wildcard=True,
        )
        facade.import_stmt_ids = [import_stmt.id]
        reg.add_all([base, facade, import_stmt])

        assert build_module_exports(reg)["pkg.facade"] == {"Visible"}

    def test_explicit_all_limits_wildcard_reexports(self):
        reg = EntityRegistry()
        base = _make_module("pkg.base", ["Included", "Excluded"])
        facade = _make_module("pkg.facade", ["Included"])
        import_stmt = PythonImportStatement(
            id="import",
            parent_id=facade.id,
            path="pkg.base",
            type="from_import",
            source_range=SourceRange(
                lineno=1, end_lineno=1, col_offset=0, end_col_offset=20
            ),
            wildcard=True,
        )
        facade.import_stmt_ids = [import_stmt.id]
        reg.add_all([base, facade, import_stmt])

        assert build_module_exports(reg)["pkg.facade"] == {"Included"}

    def test_static_all_overrides_dynamic_wildcard_dependency_for_downstream_consumer(
        self,
    ):
        reg = EntityRegistry()
        dynamic_target = _make_module("pkg.dynamic")
        dynamic_target.exports_dynamic = True
        facade = _make_module("pkg.facade", ["Public"])
        consumer = _make_module("pkg.consumer")
        public = PythonClass(
            id="public",
            parent_id=facade.id,
            name="Public",
            fqn="pkg.facade.Public",
            source_range=SourceRange(
                lineno=1, end_lineno=1, col_offset=0, end_col_offset=6
            ),
            docstring_range=None,
            visibility="public",
        )
        imports = [
            PythonImportStatement(
                id="dynamic-import",
                parent_id=facade.id,
                path="pkg.dynamic",
                type="from_import",
                source_range=SourceRange(
                    lineno=1, end_lineno=1, col_offset=0, end_col_offset=20
                ),
                wildcard=True,
            ),
            PythonImportStatement(
                id="facade-import",
                parent_id=consumer.id,
                path="pkg.facade",
                type="from_import",
                source_range=SourceRange(
                    lineno=1, end_lineno=1, col_offset=0, end_col_offset=20
                ),
                wildcard=True,
            ),
        ]
        facade.import_stmt_ids = [imports[0].id]
        consumer.import_stmt_ids = [imports[1].id]
        reg.add_all([dynamic_target, facade, consumer, public, *imports])

        exports = build_module_exports(reg)

        assert exports["pkg.facade"] == {"Public"}
        assert exports["pkg.consumer"] == {"Public"}
        assert get_dynamic_export_modules(reg) == {"pkg.dynamic"}

        context = Context()
        context.entity_registry = reg
        context.set_language("python", [".py"])
        context.set_resolver("python", PythonResolver())
        result = context.get_resolver("python").resolve(
            "pkg.consumer", "Public", context
        )

        assert result.status is ResolutionStatus.RESOLVED
        assert result.resolved_ids == {public.id}

    def test_unresolved_relative_wildcard_import_marks_module_dynamic(self):
        reg = EntityRegistry()
        module = _make_module("pkg.mod")
        import_stmt = PythonImportStatement(
            id="import",
            parent_id=module.id,
            path="....",
            type="from_import",
            source_range=SourceRange(
                lineno=1, end_lineno=1, col_offset=0, end_col_offset=4
            ),
            wildcard=True,
        )
        module.import_stmt_ids = [import_stmt.id]
        reg.add_all([module, import_stmt])

        assert get_dynamic_export_modules(reg) == {"pkg.mod"}

    def test_wildcard_cycles_are_dynamic(self):
        reg = EntityRegistry()
        first = _make_module("pkg.first")
        second = _make_module("pkg.second")
        imports = []
        for index, (module, target) in enumerate(
            ((first, "pkg.second"), (second, "pkg.first"))
        ):
            import_stmt = PythonImportStatement(
                id=f"import-{index}",
                parent_id=module.id,
                path=target,
                type="from_import",
                source_range=SourceRange(
                    lineno=1, end_lineno=1, col_offset=0, end_col_offset=20
                ),
                wildcard=True,
            )
            module.import_stmt_ids = [import_stmt.id]
            imports.append(import_stmt)
        reg.add_all([first, second, *imports])

        assert get_dynamic_export_modules(reg) == {"pkg.first", "pkg.second"}
