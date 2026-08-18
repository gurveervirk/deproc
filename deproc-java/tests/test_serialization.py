"""Tests for Java entity serialization."""

from deproc.core.interfaces.parser.models import Signature, SourceRange
from deproc.plugins.java.linker.models import JavaPackage
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
    JavaModule,
    JavaRecord,
    JavaRecordComponent,
    SimpleBinding,
)
from deproc.plugins.java.utils.serialization import (
    entity_to_record,
    record_to_entity,
)


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
        _, back = self._roundtrip(cls)
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
        _, back = self._roundtrip(iface)
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
        _, back = self._roundtrip(enum)
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
            property_ids=["f1"],
            method_ids=["c1"],
        )
        record, back = self._roundtrip(enum)
        assert record["type"] == "ENUM"
        assert back.enum_constant_ids == ["ec1", "ec2"]
        assert back.property_ids == ["f1"]
        assert back.method_ids == ["c1"]

    def test_record_roundtrip(self):
        record_obj = JavaRecord(
            id="rec_1",
            name="Point",
            fqn="com.example.Point",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            record_component_ids=["rc1"],
            property_ids=["f1"],
            method_ids=["c1"],
        )
        record, back = self._roundtrip(record_obj)
        assert record["type"] == "RECORD"
        assert back.record_component_ids == ["rc1"]
        assert back.property_ids == ["f1"]
        assert back.method_ids == ["c1"]

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
            signature=Signature(
                signature_range=_sr(2, 2),
                arguments_range=_sr(3, 3),
                return_type_range=_sr(4, 4),
            ),
            exceptions=["IOException"],
            is_static=True,
            is_synchronized=True,
        )
        record, back = self._roundtrip(method)
        assert record["type"] == "METHOD"
        assert back.signature is not None
        assert back.signature.signature_range.lineno == 2
        assert back.signature.arguments_range is not None
        assert back.signature.arguments_range.lineno == 3
        assert back.signature.return_type_range is not None
        assert back.signature.return_type_range.lineno == 4
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
        )
        record, back = self._roundtrip(ctor)
        assert record["type"] == "CONSTRUCTOR"
        assert back.signature is None

    def test_field_roundtrip(self):
        field = JavaField(
            id="f_1",
            type="FIELD",
            source_range=_sr(),
            variable_binding=SimpleBinding(
                name="count", fqn="com.example.MyClass.count"
            ),
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
            variable_binding=SimpleBinding(
                name="cache", fqn="com.example.MyClass.cache"
            ),
            value_range=None,
            type_annotation=None,
            is_transient=True,
            is_volatile=True,
        )
        _, back = self._roundtrip(field)
        assert back.is_transient is True
        assert back.is_volatile is True

    def test_enum_constant_roundtrip(self):
        const = JavaEnumConstant(
            id="ec_1",
            name="RED",
            fqn="com.example.Color.RED",
            source_range=_sr(),
            arguments_range=_sr(2, 2),
        )
        record, back = self._roundtrip(const)
        assert record["type"] == "ENUM_CONSTANT"
        assert back.arguments_range is not None
        assert back.arguments_range.lineno == 2
        assert back.name == "RED"

    def test_record_component_roundtrip(self):
        comp = JavaRecordComponent(
            id="rc_1",
            name="x",
            fqn="com.example.Point.x",
            source_range=_sr(),
            type_annotation=None,
        )
        record, back = self._roundtrip(comp)
        assert record["type"] == "RECORD_COMPONENT"
        assert isinstance(back, JavaRecordComponent)
        assert back.name == "x"
        assert back.fqn == "com.example.Point.x"

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

    def test_module_roundtrip(self):
        mod = JavaModule(
            id="mod_1",
            module_name="com.example.myapp",
            path="module-info.java",
            requires=["java.sql"],
            requires_static=["java.logging"],
            requires_transitive=["com.core"],
            exports=["com.api"],
            qualified_exports={"com.api.impl": ["com.other"]},
            opens=["com.internal"],
            qualified_opens={"com.internal2": ["com.other"]},
            uses=["com.spi.Service"],
            provides={"com.spi.Service": ["com.impl.A", "com.impl.B"]},
            compilation_unit_ids=["cu_1"],
            package_ids=["pkg_1"],
        )
        record, back = self._roundtrip(mod)
        assert record["type"] == "MODULE"
        assert back.module_name == "com.example.myapp"
        assert back.requires == ["java.sql"]
        assert back.requires_static == ["java.logging"]
        assert back.requires_transitive == ["com.core"]
        assert back.exports == ["com.api"]
        assert back.qualified_exports == {"com.api.impl": ["com.other"]}
        assert back.opens == ["com.internal"]
        assert back.qualified_opens == {"com.internal2": ["com.other"]}
        assert back.uses == ["com.spi.Service"]
        assert back.provides == {"com.spi.Service": ["com.impl.A", "com.impl.B"]}
        assert back.compilation_unit_ids == ["cu_1"]
        assert back.package_ids == ["pkg_1"]

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
        result = record_to_entity(
            {
                "id": "x",
                "type": "NOPE",
                "name": "x",
                "full_path": "x",
                "metadata_json": "{}",
            }
        )
        assert result is None
