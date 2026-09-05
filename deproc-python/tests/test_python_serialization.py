from deproc.plugins.python.parser.models import PythonConstant, PythonTypeAlias
from deproc.plugins.python.utils.serialization import record_to_entity


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
