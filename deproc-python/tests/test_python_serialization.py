from deproc.plugins.python.linker.models import PythonPackage
from deproc.plugins.python.parser.models import (
    PythonConstant,
    PythonModule,
    PythonTypeAlias,
)
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
