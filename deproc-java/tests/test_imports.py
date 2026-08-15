from deproc.plugins.java.utils.imports import resolve_java_import


class TestResolveJavaImport:
    def test_single_type(self):
        assert (
            resolve_java_import("com.example.Foo", "single_type") == "com.example.Foo"
        )

    def test_on_demand(self):
        assert resolve_java_import("com.example.*", "on_demand") == "com.example"

    def test_on_demand_no_wildcard(self):
        assert resolve_java_import("com.example", "on_demand") == "com.example"

    def test_single_static(self):
        assert (
            resolve_java_import("com.example.Foo.bar", "single_static")
            == "com.example.Foo"
        )

    def test_static_on_demand(self):
        assert (
            resolve_java_import("com.example.Foo.*", "static_on_demand")
            == "com.example.Foo"
        )

    def test_static_on_demand_no_wildcard(self):
        assert (
            resolve_java_import("com.example.Foo", "static_on_demand")
            == "com.example.Foo"
        )

    def test_java_lang_single_type(self):
        assert (
            resolve_java_import("java.lang.String", "single_type") == "java.lang.String"
        )

    def test_java_lang_static_on_demand(self):
        assert (
            resolve_java_import("java.lang.Math.*", "static_on_demand")
            == "java.lang.Math"
        )
