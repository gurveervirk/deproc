"""Tests for Java entity serialization."""

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
    JavaParameter,
    JavaRecord,
    SimpleBinding,
)
from deproc.plugins.java.linker.models import JavaPackage
from deproc.plugins.java.utils.serialization import (
    entity_to_record,
    record_to_entity,
)
from deproc.core.interfaces.parser.models import SourceRange

def _sr(lineno=1, end=1) -> SourceRange:
    return SourceRange(lineno=lineno, end_lineno=end, col_offset=0, end_col_offset=1)

class TestSerialization:
    def _roundtrip(self, entity):
        record = entity_to_record(entity)
        assert record is not None
        back = record_to_entity(record)
        assert back is not None
        assert back.id == entity.id
        return record, back

    def test_import_roundtrip(self):
        imp = JavaImport(
            id="imp_1",
            import_path="java.util.List",
            import_kind="single_type",
            imported_name="List",
            source_range=_sr(),
        )
        record, back = self._roundtrip(imp)
        assert record["type"] == "IMPORT"
        assert back.import_path == "java.util.List"
        assert back.import_kind == "single_type"
        assert back.imported_name == "List"

    def test_class_roundtrip(self):
        cls = JavaClass(
            id="cls_1",
            name="MyClass",
            fqn="com.example.MyClass",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            superclass="Base",
            implements=["I1"],
            is_abstract=False,
            is_final=True,
        )
        record, back = self._roundtrip(cls)
        assert record["type"] == "CLASS"
        assert back.name == "MyClass"
        assert back.fqn == "com.example.MyClass"
        assert back.superclass == "Base"
        assert back.implements == ["I1"]
        assert back.is_final is True

    def test_class_inner_types_roundtrip(self):
        cls = JavaClass(
            id="cls_1",
            name="Outer",
            fqn="com.example.Outer",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            inner_type_ids=["inner_1"],
        )
        record, back = self._roundtrip(cls)
        assert back.inner_type_ids == ["inner_1"]

    def test_static_nested_class_roundtrip(self):
        cls = JavaClass(
            id="cls_1",
            name="StaticNested",
            fqn="com.example.Outer.StaticNested",
            source_range=_sr(),
            docstring_range=None,
            visibility="package-private",
            is_static=True,
        )
        record, back = self._roundtrip(cls)
        assert record["type"] == "CLASS"
        assert back.is_static is True

    def test_interface_inner_types_roundtrip(self):
        iface = JavaInterface(
            id="if_1",
            name="Outer",
            fqn="com.example.Outer",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            inner_type_ids=["inner_1"],
        )
        record, back = self._roundtrip(iface)
        assert back.inner_type_ids == ["inner_1"]

    def test_enum_inner_types_roundtrip(self):
        enum = JavaEnum(
            id="en_1",
            name="Outer",
            fqn="com.example.Outer",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            inner_type_ids=["inner_1"],
        )
        record, back = self._roundtrip(enum)
        assert back.inner_type_ids == ["inner_1"]

    def test_interface_roundtrip(self):
        iface = JavaInterface(
            id="if_1",
            name="MyInterface",
            fqn="com.example.MyInterface",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            extends_interfaces=["I1", "I2"],
        )
        record, back = self._roundtrip(iface)
        assert record["type"] == "INTERFACE"
        assert back.extends_interfaces == ["I1", "I2"]

    def test_enum_roundtrip(self):
        enum = JavaEnum(
            id="en_1",
            name="Color",
            fqn="com.example.Color",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            implements=["I1"],
            enum_constant_ids=["ec1", "ec2"],
        )
        record, back = self._roundtrip(enum)
        assert record["type"] == "ENUM"
        assert back.enum_constant_ids == ["ec1", "ec2"]

    def test_record_roundtrip(self):
        record_obj = JavaRecord(
            id="rec_1",
            name="Point",
            fqn="com.example.Point",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            record_component_ids=["rc1"],
        )
        record, back = self._roundtrip(record_obj)
        assert record["type"] == "RECORD"
        assert back.record_component_ids == ["rc1"]

    def test_annotation_type_roundtrip(self):
        anno = JavaAnnotationType(
            id="an_1",
            name="MyAnno",
            fqn="com.example.MyAnno",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
        )
        record, back = self._roundtrip(anno)
        assert record["type"] == "ANNOTATION_TYPE"
        assert back.name == "MyAnno"

    def test_method_roundtrip(self):
        method = JavaMethod(
            id="m_1",
            name="getName",
            fqn="com.example.MyClass.getName",
            type="METHOD",
            source_range=_sr(),
            docstring_range=None,
            signature=None,
            return_type="String",
            parameters=[
                JavaParameter(name="x", type_fqn="int"),
                JavaParameter(name="rest", type_fqn="String", is_varargs=True),
            ],
            exceptions=["IOException"],
            is_static=True,
            is_synchronized=True,
        )
        record, back = self._roundtrip(method)
        assert record["type"] == "METHOD"
        assert back.return_type == "String"
        assert len(back.parameters) == 2
        assert back.parameters[1].is_varargs is True
        assert back.exceptions == ["IOException"]
        assert back.is_static is True

    def test_constructor_roundtrip(self):
        ctor = JavaMethod(
            id="c_1",
            name="MyClass",
            fqn="com.example.MyClass.MyClass",
            type="CONSTRUCTOR",
            source_range=_sr(),
            docstring_range=None,
            signature=None,
            return_type=None,
        )
        record, back = self._roundtrip(ctor)
        assert record["type"] == "CONSTRUCTOR"
        assert back.return_type is None

    def test_field_roundtrip(self):
        field = JavaField(
            id="f_1",
            type="FIELD",
            source_range=_sr(),
            variable_binding=SimpleBinding(name="count", fqn="com.example.MyClass.count"),
            value_range=None,
            type_annotation=None,
            is_static=True,
            is_final=True,
        )
        record, back = self._roundtrip(field)
        assert record["type"] == "FIELD"
        assert back.variable_binding.name == "count"
        assert back.is_static is True

    def test_field_modifiers_roundtrip(self):
        field = JavaField(
            id="f_1",
            type="FIELD",
            source_range=_sr(),
            variable_binding=SimpleBinding(name="cache", fqn="com.example.MyClass.cache"),
            value_range=None,
            type_annotation=None,
            is_transient=True,
            is_volatile=True,
        )
        _, back = self._roundtrip(field)
        assert back.is_transient is True
        assert back.is_volatile is True

    def test_enum_constant_roundtrip(self):
        const = JavaField(
            id="ec_1",
            type="ENUM_CONSTANT",
            source_range=_sr(),
            variable_binding=SimpleBinding(name="RED", fqn="com.example.Color.RED"),
            value_range=None,
            type_annotation=None,
        )
        record, back = self._roundtrip(const)
        assert record["type"] == "ENUM_CONSTANT"

    def test_record_component_roundtrip(self):
        comp = JavaField(
            id="rc_1",
            type="RECORD_COMPONENT",
            source_range=_sr(),
            variable_binding=SimpleBinding(name="x", fqn="com.example.Point.x"),
            value_range=None,
            type_annotation=None,
        )
        record, back = self._roundtrip(comp)
        assert record["type"] == "RECORD_COMPONENT"

    def test_compilation_unit_roundtrip(self):
        cu = JavaCompilationUnit(
            id="cu_1",
            fqn="com.example.MyClass",
            package_fqn="com.example",
            path="com/example/MyClass.java",
            source="",
            docstring_range=None,
        )
        record, back = self._roundtrip(cu)
        assert record["type"] == "COMPILATION_UNIT"
        assert back.package_fqn == "com.example"
        assert back.fqn == "com.example.MyClass"

    def test_package_roundtrip(self):
        pkg = JavaPackage(
            id="pkg_1",
            path="com/example",
            fqn="com.example",
            subpackage_ids=["sub_1"],
            compilation_unit_ids=["cu_1"],
        )
        record, back = self._roundtrip(pkg)
        assert record["type"] == "PACKAGE"
        assert back.subpackage_ids == ["sub_1"]
        assert back.compilation_unit_ids == ["cu_1"]

    def test_unknown_type_returns_none(self):
        from deproc.core.interfaces.parser.models import Entity
        result = record_to_entity({"id": "x", "type": "NOPE", "name": "x", "full_path": "x", "metadata_json": "{}"})
        assert result is None
