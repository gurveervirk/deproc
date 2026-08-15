from deproc.plugins.python.utils.imports import resolve_relative_import_path


class TestResolveRelativeImportPath:
    def test_single_dot_module(self):
        assert (
            resolve_relative_import_path(".sibling", "pkg.sub.mod", False)
            == "pkg.sub.sibling"
        )

    def test_single_dot_nested(self):
        assert (
            resolve_relative_import_path(".subpkg.module", "pkg.sub.mod", False)
            == "pkg.sub.subpkg.module"
        )

    def test_double_dot(self):
        assert (
            resolve_relative_import_path("..sibling", "pkg.sub.mod", False)
            == "pkg.sibling"
        )

    def test_triple_dot(self):
        assert (
            resolve_relative_import_path("...sibling", "pkg.sub.mod", False)
            == "sibling"
        )

    def test_single_dot_in_package(self):
        assert (
            resolve_relative_import_path(".module", "package", True) == "package.module"
        )

    def test_double_dot_in_package(self):
        assert (
            resolve_relative_import_path("..other", "package.subpackage", True)
            == "package.other"
        )

    def test_triple_dot_in_package(self):
        assert (
            resolve_relative_import_path("...sibling", "pkg.sub.mod", True)
            == "pkg.sibling"
        )

    def test_empty_parent_parts(self):
        assert resolve_relative_import_path("...sibling", "pkg", True) == "sibling"

    def test_quadruple_dot(self):
        assert resolve_relative_import_path("....deep", "a.b.c.d.e", False) == "a.deep"
