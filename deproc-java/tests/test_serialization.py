"""Tests for Java entity serialization."""

import json

from deproc.core.context import Context
from deproc.core.interfaces.parser.models import (
    Annotation,
    Signature,
    SourceRange,
)
from deproc.core.runtime.registries.entity import EntityRegistry
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
    JavaPackageInfo,
    JavaRecord,
    JavaRecordComponent,
    SimpleBinding,
)
from deproc.plugins.java.resolver.main import JavaResolver
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
            source_range=SourceRange(
                lineno=1,
                end_lineno=1,
                col_offset=0,
                end_col_offset=1,
                source_id="source-id",
            ),
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
        assert back.source_range.source_id == "source-id"
        assert back.superclass == "Base"
        assert back.implements == ["I1"]
        assert back.is_final is True

        metadata = json.loads(record["metadata_json"])
        assert metadata["superclass"] == "Base"
        assert metadata["implements"] == ["I1"]

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
            visibility="protected",
            is_static=True,
            is_final=True,
        )
        record, back = self._roundtrip(field)
        assert record["type"] == "FIELD"
        assert back.variable_binding.name == "count"
        assert back.visibility == "protected"
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
        assert record["type"] == "JAVA_MODULE"
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
            package_info_id="pi_1",
        )
        record, back = self._roundtrip(pkg)
        assert record["type"] == "PACKAGE"
        assert back.subpackage_ids == ["sub_1"]
        assert back.compilation_unit_ids == ["cu_1"]
        assert back.package_info_id == "pi_1"

    def test_package_info_roundtrip(self):
        pi = JavaPackageInfo(
            id="pi_1",
            fqn="com.example.models.package-info",
            package_fqn="com.example.models",
            path="com/example/models/package-info.java",
            source="",
            docstring_range=None,
        )
        record, back = self._roundtrip(pi)
        assert record["type"] == "PACKAGE_INFO"
        assert record["full_path"] == "com.example.models.package-info"
        meta = json.loads(record["metadata_json"])
        assert meta["package_fqn"] == "com.example.models"
        assert meta["path"] == "com/example/models/package-info.java"
        assert back.fqn == "com.example.models.package-info"
        assert back.package_fqn == "com.example.models"

    def test_package_info_with_annotations_roundtrip(self):
        sr = SourceRange(lineno=2, end_lineno=2, col_offset=0, end_col_offset=12)
        pi = JavaPackageInfo(
            id="pi_2",
            fqn="com.example.api.package-info",
            package_fqn="com.example.api",
            path="com/example/api/package-info.java",
            source="",
            docstring_range=None,
            annotations=[Annotation(name="@Deprecated", source_range=sr)],
        )
        record, back = self._roundtrip(pi)
        assert record["type"] == "PACKAGE_INFO"
        meta = json.loads(record["metadata_json"])
        assert meta["annotations"] == ["@Deprecated"]
        assert back.fqn == "com.example.api.package-info"

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

    def test_semantic_queries_survive_round_trip(self):
        owner_cu = JavaCompilationUnit(
            id="owner-cu",
            fqn="com.example.Use",
            package_fqn="com.example",
            path="com/example/Use.java",
            source="",
            docstring_range=None,
            import_stmt_ids=["base-import", "contract-import"],
            type_ids=["owner"],
        )
        base_import = JavaImport(
            id="base-import",
            parent_id=owner_cu.id,
            import_path="p.Base",
            import_kind="single_type",
            imported_name="Base",
            source_range=_sr(),
        )
        contract_import = JavaImport(
            id="contract-import",
            parent_id=owner_cu.id,
            import_path="p.Contract",
            import_kind="single_type",
            imported_name="Contract",
            source_range=_sr(),
        )
        owner = JavaClass(
            id="owner",
            parent_id=owner_cu.id,
            name="Use",
            fqn="com.example.Use",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
            superclass="Base",
            implements=["Contract"],
        )
        target_cu = JavaCompilationUnit(
            id="target-cu",
            fqn="p.Base",
            package_fqn="p",
            path="p/Base.java",
            source="",
            docstring_range=None,
            type_ids=["base", "contract"],
        )
        base = JavaClass(
            id="base",
            parent_id=target_cu.id,
            name="Base",
            fqn="p.Base",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
        )
        contract = JavaInterface(
            id="contract",
            parent_id=target_cu.id,
            name="Contract",
            fqn="p.Contract",
            source_range=_sr(),
            docstring_range=None,
            visibility="public",
        )
        entities = [
            owner_cu,
            base_import,
            contract_import,
            owner,
            target_cu,
            base,
            contract,
        ]

        def make_context(items):
            context = Context()
            context.set_language("java", [".java"])
            context.set_resolver("java", JavaResolver())
            context.entity_registry = EntityRegistry()
            context.entity_registry.add_all(items)
            return context

        original = make_context(entities)
        original_resolver = original.get_resolver("java")
        original_symbol = original_resolver.resolve("com.example.Use", "Base", original)
        original_type = original_resolver.resolve_type_reference(
            "Base", owner, original
        )
        records = [
            record
            for entity in entities
            if (record := entity_to_record(entity, registry=original.entity_registry))
            is not None
        ]
        restored_entities = [record_to_entity(record) for record in records]
        restored = make_context(restored_entities)
        restored_owner = restored.entity_registry.get("owner")
        restored_resolver = restored.get_resolver("java")
        restored_symbol = restored_resolver.resolve("com.example.Use", "Base", restored)
        restored_type = restored_resolver.resolve_type_reference(
            "Base", restored_owner, restored
        )

        assert (
            original_symbol.status,
            original_symbol.candidates,
            original_symbol.reason,
        ) == (
            restored_symbol.status,
            restored_symbol.candidates,
            restored_symbol.reason,
        )
        assert (
            original_type.status,
            original_type.value,
            original_type.candidates,
            original_type.reason,
        ) == (
            restored_type.status,
            restored_type.value,
            restored_type.candidates,
            restored_type.reason,
        )
        assert restored_owner.superclass == owner.superclass
        assert restored_owner.implements == owner.implements
