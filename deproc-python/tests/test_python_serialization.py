from deproc.core.context import Context
from deproc.core.interfaces.parser.models import SourceRange
from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.plugins.python.linker.models import PythonPackage
from deproc.plugins.python.parser.models import (
    PythonClass,
    PythonConstant,
    PythonImportStatement,
    PythonModule,
    PythonTypeAlias,
)
from deproc.plugins.python.resolver.main import PythonResolver
from deproc.plugins.python.utils.exports import build_module_exports
from deproc.plugins.python.utils.serialization import (
    entity_to_record,
    record_to_entity,
)


def test_record_to_entity_restores_variable_binding_fqn():
    record = {
        "id": "constant-id",
        "full_path": "pkg.VALUE",
        "name": "VALUE",
        "type": "CONSTANT",
        "metadata_json": '{"fqn":"pkg.VALUE","lineno":1}',
        "parent_id": "module-id",
    }

    entity = record_to_entity(record)

    assert isinstance(entity, PythonConstant)
    assert entity.parent_id == "module-id"
    assert entity.variable_binding.fqn == "pkg.VALUE"


def test_record_to_entity_restores_type_alias_binding():
    record = {
        "id": "alias-id",
        "full_path": "pkg.UserId",
        "name": "UserId",
        "type": "TYPE_ALIAS",
        "metadata_json": '{"fqn":"pkg.UserId","lineno":1}',
        "parent_id": "module-id",
    }

    entity = record_to_entity(record)

    assert isinstance(entity, PythonTypeAlias)
    assert entity.variable_binding.fqn == "pkg.UserId"


def test_serialize_round_trip_restores_module_ownership_and_exports():
    record = entity_to_record(
        PythonModule(
            id="mod-id",
            fqn="pkg",
            path="pkg/__init__.py",
            source="",
            docstring_range=None,
            import_stmt_ids=[f"imp{i}" for i in range(3)],
            type_ids=[f"type{i}" for i in range(2)],
            function_ids=[f"fn{i}" for i in range(2)],
            variable_ids=[f"var{i}" for i in range(2)],
            control_flow_group_ids=["group1"],
            all_exports=["User"],
            exports_dynamic=True,
        )
    )
    assert record is not None

    entity = record_to_entity(record)

    assert isinstance(entity, PythonModule)
    assert entity.fqn == "pkg"
    assert entity.import_stmt_ids == ["imp0", "imp1", "imp2"]
    assert entity.type_ids == ["type0", "type1"]
    assert entity.function_ids == ["fn0", "fn1"]
    assert entity.variable_ids == ["var0", "var1"]
    assert entity.control_flow_group_ids == ["group1"]
    assert entity.all_exports == ["User"]
    assert entity.exports_dynamic is True


def test_serialize_round_trip_restores_package_submodules():
    record = entity_to_record(
        PythonPackage(
            id="pkg-id",
            fqn="pkg",
            path="pkg/__init__.py",
            source="",
            docstring_range=None,
            submodule_ids=["sub1", "sub2"],
            import_stmt_ids=["imp1"],
        )
    )
    assert record is not None

    entity = record_to_entity(record)

    assert isinstance(entity, PythonPackage)
    assert entity.fqn == "pkg"
    assert entity.submodule_ids == ["sub1", "sub2"]
    assert entity.import_stmt_ids == ["imp1"]


def test_semantic_queries_survive_round_trip():
    source_range = SourceRange(lineno=1, end_lineno=1, col_offset=0, end_col_offset=1)
    base_module = PythonModule(
        id="base-module",
        fqn="pkg.base",
        path="pkg/base.py",
        source="",
        docstring_range=None,
        all_exports=["Base"],
        type_ids=["base"],
    )
    base = PythonClass(
        id="base",
        parent_id=base_module.id,
        name="Base",
        fqn="pkg.base.Base",
        source_range=source_range,
        docstring_range=None,
        visibility="public",
    )
    facade = PythonModule(
        id="facade-module",
        fqn="pkg.facade",
        path="pkg/facade.py",
        source="",
        docstring_range=None,
        all_exports=["Base"],
        import_stmt_ids=["star-import"],
    )
    star_import = PythonImportStatement(
        id="star-import",
        parent_id=facade.id,
        path="pkg.base",
        type="from_import",
        wildcard=True,
        source_range=source_range,
    )
    child_module = PythonModule(
        id="child-module",
        fqn="pkg.child",
        path="pkg/child.py",
        source="",
        docstring_range=None,
        type_ids=["child"],
    )
    child = PythonClass(
        id="child",
        parent_id=child_module.id,
        name="Child",
        fqn="pkg.child.Child",
        source_range=source_range,
        docstring_range=None,
        visibility="public",
        inherits=["pkg.base.Base"],
    )
    entities = [base_module, base, facade, star_import, child_module, child]

    def make_context(items):
        context = Context()
        context.set_language("python", [".py"])
        context.set_resolver("python", PythonResolver())
        context.entity_registry = EntityRegistry()
        context.entity_registry.add_all(items)
        return context

    original = make_context(entities)
    original_resolver = original.get_resolver("python")
    original_result = original_resolver.resolve("pkg.facade", "Base", original)
    original_mro = original_resolver._class_mro_ids("child", original, {}, set())
    module_exports = build_module_exports(original.entity_registry)
    records = [
        record
        for entity in entities
        if (
            record := entity_to_record(
                entity,
                module_exports=module_exports,
                registry=original.entity_registry,
            )
        )
        is not None
    ]
    restored = make_context([record_to_entity(record) for record in records])
    restored_resolver = restored.get_resolver("python")
    restored_result = restored_resolver.resolve("pkg.facade", "Base", restored)
    restored_mro = restored_resolver._class_mro_ids("child", restored, {}, set())

    assert (
        original_result.status,
        original_result.candidates,
        original_result.reason,
    ) == (
        restored_result.status,
        restored_result.candidates,
        restored_result.reason,
    )
    assert original_mro == restored_mro == ["child", "base"]
