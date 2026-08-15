"""Tests for Java parser."""

import os
import tempfile

from deproc.core.context import Context
from deproc.plugins.java.parser import JavaSourceParser
from deproc.plugins.java.parser.models import (
    JavaAnnotationType,
    JavaClass,
    JavaCompilationUnit,
    JavaEnum,
    JavaEnumConstant,
    JavaField,
    JavaImport,
    JavaInterface,
    JavaMethod,
    JavaRecord,
    JavaRecordComponent,
)

parser = JavaSourceParser()


def _parse(
    code: str, base_path: str | None = None
) -> tuple[JavaCompilationUnit, Context]:
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "Test.java")
    with open(path, "w") as f:
        f.write(code)
    ctx = Context(base_path=base_path or tmp_dir)
    ctx.set_language("java", ["java"])
    cu = parser.parse_file(path, ctx)
    return cu, ctx


def _entity_of_type(ctx: Context, cls) -> list:
    return [e for e in ctx.entity_registry.values() if isinstance(e, cls)]


class TestParser:
    def test_parse_simple_class(self):
        code = """
class MyClass {
    int x;
}
"""
        cu, ctx = _parse(code)
        assert cu is not None
        classes = _entity_of_type(ctx, JavaClass)
        assert len(classes) == 1
        assert classes[0].name == "MyClass"

    def test_parse_empty_code(self):
        cu, _ = _parse("")
        assert cu is not None

    def test_parse_file_does_not_exist(self):
        import pytest

        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/foo.java", Context())

    def test_parse_wrong_extension(self):
        import tempfile as tf

        import pytest

        with tf.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write("x")
        try:
            with pytest.raises(ValueError):
                parser.parse_file(tmp.name, Context())
        finally:
            os.unlink(tmp.name)

    def test_entities_have_source_id(self):
        code = """
package com.example;

import java.util.List;

public class MyClass {
    private List<String> names;
    public void m() {}
}
"""
        cu, ctx = _parse(code)
        for entity in ctx.entity_registry.values():
            sr = getattr(entity, "source_range", None)
            if sr is not None:
                assert sr.source_id == cu.id, (
                    f"{type(entity).__name__} missing source_id"
                )


class TestPackageAndFqn:
    def test_package_declaration(self):
        cu, _ = _parse("package com.example.foo;\nclass MyClass {}\n")
        assert cu.package_fqn == "com.example.foo"

    def test_fqn_with_package(self):
        code = "package com.example.foo;\nclass MyClass {}\n"
        _, ctx = _parse(code)
        classes = _entity_of_type(ctx, JavaClass)
        assert classes[0].fqn == "com.example.foo.MyClass"

    def test_unnamed_package(self):
        code = "class MyClass {}\n"
        cu, _ = _parse(code)
        assert cu.package_fqn is None

    def test_fqn_unnamed_package(self):
        code = "class MyClass {}\n"
        _, ctx = _parse(code)
        classes = _entity_of_type(ctx, JavaClass)
        assert classes[0].fqn == "MyClass"


class TestImports:
    def test_single_type_import(self):
        code = "import java.util.List;\nclass MyClass {}\n"
        _, ctx = _parse(code)
        imports = _entity_of_type(ctx, JavaImport)
        assert len(imports) == 1
        assert imports[0].import_kind == "single_type"
        assert imports[0].import_path == "java.util.List"
        assert imports[0].imported_name == "List"

    def test_on_demand_import(self):
        code = "import java.util.*;\nclass MyClass {}\n"
        _, ctx = _parse(code)
        imports = _entity_of_type(ctx, JavaImport)
        assert imports[0].import_kind == "on_demand"
        assert imports[0].import_path == "java.util.*"
        assert imports[0].imported_name is None

    def test_single_static_import(self):
        code = "import static java.lang.Math.max;\nclass MyClass {}\n"
        _, ctx = _parse(code)
        imports = _entity_of_type(ctx, JavaImport)
        assert imports[0].import_kind == "single_static"
        assert imports[0].import_path == "java.lang.Math.max"
        assert imports[0].imported_name == "max"

    def test_static_on_demand_import(self):
        code = "import static java.lang.Math.*;\nclass MyClass {}\n"
        _, ctx = _parse(code)
        imports = _entity_of_type(ctx, JavaImport)
        assert imports[0].import_kind == "static_on_demand"
        assert imports[0].import_path == "java.lang.Math.*"
        assert imports[0].imported_name is None

    def test_imports_attached_to_cu(self):
        code = "import java.util.List;\nimport java.util.Map;\nclass MyClass {}\n"
        cu, _ = _parse(code)
        assert len(cu.import_stmt_ids) == 2


class TestTypeExtraction:
    def test_class_with_superclass_and_interfaces(self):
        code = """
public class MyClass extends Base implements I1, I2 {
}
"""
        _, ctx = _parse(code)
        classes = _entity_of_type(ctx, JavaClass)
        cls = classes[0]
        assert cls.superclass == "Base"
        assert cls.implements == ["I1", "I2"]
        assert cls.visibility == "public"

    def test_class_modifiers(self):
        code = """
public abstract final class MyClass {
}
"""
        _, ctx = _parse(code)
        cls = _entity_of_type(ctx, JavaClass)[0]
        assert cls.is_abstract is True

    def test_interface_extends(self):
        code = """
interface MyInterface extends I1, I2 {
}
"""
        _, ctx = _parse(code)
        ifaces = _entity_of_type(ctx, JavaInterface)
        assert ifaces[0].extends_interfaces == ["I1", "I2"]
        assert ifaces[0].visibility == "package-private"

    def test_enum(self):
        code = """
enum Color implements I1 {
    RED(1), GREEN(2);
    private final int code;
    Color(int c) { this.code = c; }
}
"""
        _, ctx = _parse(code)
        enums = _entity_of_type(ctx, JavaEnum)
        enum = enums[0]
        assert enum.implements == ["I1"]
        assert len(enum.enum_constant_ids) == 2
        assert len(enum.property_ids) == 1
        constructors = _entity_of_type(ctx, JavaMethod)
        assert len([c for c in constructors if c.type == "CONSTRUCTOR"]) == 1
        constants = _entity_of_type(ctx, JavaEnumConstant)
        assert len(constants) == 2
        assert constants[0].name == "RED"
        assert constants[1].name == "GREEN"

    def test_enum_constant_arguments_range(self):
        code = """
enum Color {
    RED(255, 0, 0, "red"),
    GREEN(0, 255, 0);
}
"""
        _, ctx = _parse(code)
        constants = _entity_of_type(ctx, JavaEnumConstant)
        by_name = {c.name: c for c in constants}
        red = by_name["RED"]
        green = by_name["GREEN"]
        assert red.arguments_range is not None
        assert red.arguments_range.lineno == 3
        assert red.arguments_range.end_col_offset - red.arguments_range.col_offset == len('(255, 0, 0, "red")')
        assert green.arguments_range is not None
        assert green.arguments_range.lineno == 4

    def test_record(self):
        code = """
record Point(int x, int y) implements I1 {
}
"""
        _, ctx = _parse(code)
        records = _entity_of_type(ctx, JavaRecord)
        record = records[0]
        assert record.implements == ["I1"]
        assert len(record.record_component_ids) == 2
        components = _entity_of_type(ctx, JavaRecordComponent)
        assert len(components) == 2
        assert components[0].name == "x"
        assert components[0].type_annotation is not None

    def test_record_component_type_annotation(self):
        code = """
record Point(int x, java.util.List<String> names) {
}
"""
        _, ctx = _parse(code)
        components = _entity_of_type(ctx, JavaRecordComponent)
        by_name = {c.name: c for c in components}
        assert by_name["names"].type_annotation is not None
        assert by_name["x"].type_annotation is not None

    def test_annotation_type(self):
        code = """
@interface MyAnno {
    String value() default "";
}
"""
        _, ctx = _parse(code)
        annos = _entity_of_type(ctx, JavaAnnotationType)
        assert len(annos) == 1
        assert annos[0].name == "MyAnno"

    def test_multiple_top_level_types(self):
        code = """
class A {}
interface B {}
enum C {}
record D() {}
@interface E {}
"""
        cu, _ = _parse(code)
        assert len(cu.type_ids) == 5


class TestMembers:
    def test_method(self):
        code = """
class MyClass {
    public String getName(int x) throws IOException {
        return null;
    }
}
"""
        _, ctx = _parse(code)
        methods = _entity_of_type(ctx, JavaMethod)
        method = next(m for m in methods if m.type == "METHOD")
        assert method.name == "getName"
        assert method.return_type == "String"
        assert method.exceptions == ["IOException"]
        assert method.visibility == "public"

    def test_method_varargs(self):
        code = """
class MyClass {
    public void m(String... rest) {}
}
"""
        _, ctx = _parse(code)
        methods = _entity_of_type(ctx, JavaMethod)
        method = [m for m in methods if m.type == "METHOD"][0]
        assert method.signature is not None
        assert method.signature.arguments_range is not None

    def test_constructor(self):
        code = """
class MyClass {
    public MyClass(String name) {
        this.name = name;
    }
}
"""
        _, ctx = _parse(code)
        classes = _entity_of_type(ctx, JavaClass)
        cls = classes[0]
        constructors = _entity_of_type(ctx, JavaMethod)
        ctor = [c for c in constructors if c.type == "CONSTRUCTOR"][0]
        assert len(cls.method_ids) == 1
        assert ctor.return_type is None
        assert ctor.name == "MyClass"

    def test_fields(self):
        code = """
class MyClass {
    private final String name;
    public static int COUNT = 5;
}
"""
        _, ctx = _parse(code)
        fields = _entity_of_type(ctx, JavaField)
        name_field = next(f for f in fields if f.variable_binding.name == "name")
        count_field = next(f for f in fields if f.variable_binding.name == "COUNT")
        assert name_field.is_final is True
        assert name_field.is_static is False
        assert count_field.is_static is True

    def test_field_fqn(self):
        code = """
package com.example;
class MyClass {
    int x;
}
"""
        _, ctx = _parse(code)
        fields = _entity_of_type(ctx, JavaField)
        assert fields[0].variable_binding.fqn == "com.example.MyClass.x"

    def test_method_static_synchronized(self):
        code = """
class MyClass {
    public static synchronized void m() {}
}
"""
        _, ctx = _parse(code)
        methods = _entity_of_type(ctx, JavaMethod)
        method = next(m for m in methods if m.type == "METHOD")
        assert method.is_static is True
        assert method.is_synchronized is True


class TestAnnotationsAndDocs:
    def test_class_annotations(self):
        code = """
@Deprecated
@SuppressWarnings("unused")
class MyClass {
}
"""
        _, ctx = _parse(code)
        cls = _entity_of_type(ctx, JavaClass)[0]
        names = {a.name for a in cls.annotations}
        assert names == {"Deprecated", "SuppressWarnings"}

    def test_method_annotations(self):
        code = """
class MyClass {
    @Override
    public void m() {}
}
"""
        _, ctx = _parse(code)
        methods = _entity_of_type(ctx, JavaMethod)
        method = next(m for m in methods if m.type == "METHOD")
        assert [a.name for a in method.annotations] == ["Override"]

    def test_javadoc_on_class(self):
        code = """
/**
 * Doc for MyClass
 */
class MyClass {
}
"""
        _, ctx = _parse(code)
        cls = _entity_of_type(ctx, JavaClass)[0]
        assert cls.docstring_range is not None

    def test_file_docstring(self):
        code = """
/**
 * File doc
 */
package com.example;
class MyClass {
}
"""
        cu, _ = _parse(code)
        assert cu.docstring_range is not None


class TestInnerTypes:
    def _class_by_fqn(self, ctx: Context, fqn: str) -> JavaClass:
        for e in ctx.entity_registry.values():
            if isinstance(e, JavaClass) and e.fqn == fqn:
                return e
        raise AssertionError(f"class not found: {fqn}")

    def test_static_nested_class(self):
        code = """
class Outer {
    static class StaticNested {
        int a;
    }
}
"""
        _, ctx = _parse(code)
        outer = self._class_by_fqn(ctx, "Outer")
        assert len(outer.inner_type_ids) == 1
        nested = ctx.entity_registry.get(outer.inner_type_ids[0])
        assert isinstance(nested, JavaClass)
        assert nested.name == "StaticNested"
        assert nested.fqn == "Outer.StaticNested"
        assert nested.is_static is True

    def test_member_class(self):
        code = """
class Outer {
    class Inner {
    }
}
"""
        _, ctx = _parse(code)
        outer = self._class_by_fqn(ctx, "Outer")
        assert len(outer.inner_type_ids) == 1
        inner = ctx.entity_registry.get(outer.inner_type_ids[0])
        assert isinstance(inner, JavaClass)
        assert inner.fqn == "Outer.Inner"
        assert inner.is_static is False

    def test_nested_interface(self):
        code = """
class Outer {
    interface NestedIface {
    }
}
"""
        _, ctx = _parse(code)
        outer = self._class_by_fqn(ctx, "Outer")
        assert len(outer.inner_type_ids) == 1
        nested = ctx.entity_registry.get(outer.inner_type_ids[0])
        assert isinstance(nested, JavaInterface)
        assert nested.fqn == "Outer.NestedIface"

    def test_deep_nested_chain_fqn(self):
        code = """
class Outer {
    static class A {
        class B {
        }
    }
}
"""
        _, ctx = _parse(code)
        outer = self._class_by_fqn(ctx, "Outer")
        a = ctx.entity_registry.get(outer.inner_type_ids[0])
        assert a.fqn == "Outer.A"
        assert len(a.inner_type_ids) == 1
        b = ctx.entity_registry.get(a.inner_type_ids[0])
        assert b.fqn == "Outer.A.B"

    def test_anonymous_class_in_field_initializer(self):
        code = """
class Main {
    Runnable r = new Runnable() {
        public void run() {}
    };
}
"""
        _, ctx = _parse(code)
        main = self._class_by_fqn(ctx, "Main")
        assert len(main.inner_type_ids) == 1
        anon = ctx.entity_registry.get(main.inner_type_ids[0])
        assert isinstance(anon, JavaClass)
        assert anon.name == "r"
        assert anon.fqn == "Main$1"

    def test_multiple_anonymous_classes_ordinal(self):
        code = """
class Main {
    Runnable r = new Runnable() { public void run() {} };
    Runnable r2 = new Runnable() { public void run() {} };
}
"""
        _, ctx = _parse(code)
        main = self._class_by_fqn(ctx, "Main")
        assert len(main.inner_type_ids) == 2
        anon1 = ctx.entity_registry.get(main.inner_type_ids[0])
        anon2 = ctx.entity_registry.get(main.inner_type_ids[1])
        assert anon1.fqn == "Main$1"
        assert anon1.name == "r"
        assert anon2.fqn == "Main$2"
        assert anon2.name == "r2"

    def test_anonymous_class_members(self):
        code = """
class Main {
    Runnable r = new Runnable() {
        int count = 0;
        public void run() {}
    };
}
"""
        _, ctx = _parse(code)
        main = self._class_by_fqn(ctx, "Main")
        anon = ctx.entity_registry.get(main.inner_type_ids[0])
        methods = [ctx.entity_registry.get(i) for i in anon.method_ids]
        assert [m.name for m in methods] == ["run"]
        fields = [ctx.entity_registry.get(i) for i in anon.property_ids]
        assert [f.variable_binding.name for f in fields] == ["count"]

    def test_anonymous_class_in_method_not_extracted(self):
        code = """
class Main {
    void m() {
        Runnable r = new Runnable() { public void run() {} };
    }
}
"""
        _, ctx = _parse(code)
        main = self._class_by_fqn(ctx, "Main")
        assert main.inner_type_ids == []

    def test_local_class_not_extracted(self):
        code = """
class Main {
    void m() {
        class Local {}
    }
}
"""
        _, ctx = _parse(code)
        main = self._class_by_fqn(ctx, "Main")
        assert main.inner_type_ids == []

    def test_transient_volatile_field_modifiers(self):
        code = """
class MyClass {
    transient int cache;
    volatile boolean flag;
    int normal;
}
"""
        _, ctx = _parse(code)
        fields = _entity_of_type(ctx, JavaField)
        by_name = {f.variable_binding.name: f for f in fields}
        assert by_name["cache"].is_transient is True
        assert by_name["cache"].is_volatile is False
        assert by_name["flag"].is_volatile is True
        assert by_name["flag"].is_transient is False
        assert by_name["normal"].is_transient is False
        assert by_name["normal"].is_volatile is False
