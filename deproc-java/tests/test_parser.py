"""Tests for Java parser."""

from deproc.plugins.java.parser import JavaSourceParser
from deproc.core.context import Context
from deproc.plugins.java.parser.models import (
    JavaAnnotationType,
    JavaClass,
    JavaCompilationUnit,
    JavaEnum,
    JavaField,
    JavaImport,
    JavaInterface,
    JavaMethod,
    JavaRecord,
    SimpleBinding,
)
import tempfile
import os

parser = JavaSourceParser()

def _parse(code: str, base_path: str | None = None) -> tuple[JavaCompilationUnit, Context]:
    import uuid
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
        import pytest
        import tempfile as tf
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
                assert sr.source_id == cu.id, f"{type(entity).__name__} missing source_id"

class TestPackageAndFqn:
    def test_package_declaration(self):
        cu, _ = _parse("package com.example.foo;\nclass MyClass {}\n")
        assert cu.package_fqn == "com.example.foo"

    def test_fqn_with_package(self):
        code = "package com.example.foo;\nclass MyClass {}\n"
        cu, ctx = _parse(code)
        classes = _entity_of_type(ctx, JavaClass)
        assert classes[0].fqn == "com.example.foo.MyClass"

    def test_unnamed_package(self):
        code = "class MyClass {}\n"
        cu, _ = _parse(code)
        assert cu.package_fqn is None

    def test_fqn_unnamed_package(self):
        code = "class MyClass {}\n"
        cu, ctx = _parse(code)
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
        cu, ctx = _parse(code)
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
    Color(int c) {}
}
"""
        _, ctx = _parse(code)
        enums = _entity_of_type(ctx, JavaEnum)
        enum = enums[0]
        assert enum.implements == ["I1"]
        assert len(enum.enum_constant_ids) == 2
        constants = _entity_of_type(ctx, JavaField)
        consts = [c for c in constants if c.type == "ENUM_CONSTANT"]
        assert len(consts) == 2
        assert consts[0].variable_binding.name == "RED"

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
        cu, ctx = _parse(code)
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
        method = [m for m in methods if m.type == "METHOD"][0]
        assert method.name == "getName"
        assert method.return_type == "String"
        assert len(method.parameters) == 1
        assert method.parameters[0].name == "x"
        assert method.parameters[0].type_fqn == "int"
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
        assert method.parameters[0].is_varargs is True
        assert method.parameters[0].type_fqn == "String"

    def test_constructor(self):
        code = """
class MyClass {
    public MyClass(String name) {
        this.name = name;
    }
}
"""
        cu, ctx = _parse(code)
        classes = _entity_of_type(ctx, JavaClass)
        cls = classes[0]
        assert len(cls.constructor_ids) == 1
        constructors = _entity_of_type(ctx, JavaMethod)
        ctor = [c for c in constructors if c.type == "CONSTRUCTOR"][0]
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
        name_field = [f for f in fields if f.variable_binding.name == "name"][0]
        count_field = [f for f in fields if f.variable_binding.name == "COUNT"][0]
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
        method = [m for m in methods if m.type == "METHOD"][0]
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
        method = [m for m in methods if m.type == "METHOD"][0]
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
