import json
from pathlib import Path

from deproc.core.interfaces.parser.models import (
    ControlFlowBlock,
    ControlFlowGroup,
    Entity,
    FunctionLike,
    SourceRange,
    TypeDefinition,
)

from ..linker.models import (
    JavaPackage,
)
from ..parser.models import (
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
    SimpleBinding,
)
from ..linker.models import (
    JavaPackage,
)

TYPE_TO_CLASS = {
    "CLASS": JavaClass,
    "INTERFACE": JavaInterface,
    "ENUM": JavaEnum,
    "RECORD": JavaRecord,
    "ANNOTATION_TYPE": JavaAnnotationType,
    "METHOD": JavaMethod,
    "CONSTRUCTOR": JavaMethod,
    "FIELD": JavaField,
    "ENUM_CONSTANT": JavaEnumConstant,
    "RECORD_COMPONENT": JavaRecordComponent,
    "IMPORT": JavaImport,
    "COMPILATION_UNIT": JavaCompilationUnit,
    "PACKAGE": JavaPackage,
    "CONTROL_FLOW_BLOCK": ControlFlowBlock,
    "CONTROL_FLOW_GROUP": ControlFlowGroup,
}


def _module_fqn(full_path: str) -> str | None:
    parts = full_path.rsplit(".", 1)
    return parts[0] if len(parts) > 1 else None

def _source_range_from_meta(meta: dict, prefix: str) -> SourceRange | None:
    lineno = meta.get(f"{prefix}_lineno")
    end_lineno = meta.get(f"{prefix}_end_lineno")
    if lineno is None or end_lineno is None:
        return None
    return SourceRange(
        lineno=lineno,
        end_lineno=end_lineno,
        col_offset=meta.get(f"{prefix}_col_offset", 0),
        end_col_offset=meta.get(f"{prefix}_end_col_offset", 0),
    )

def entity_to_record(entity, language: str = "java", module_exports: dict[str, set[str]] | None = None, registry=None) -> dict | None:
    if isinstance(entity, JavaImport):
        name = entity.imported_name or entity.import_path
        full_path = entity.import_path
        entity_type = "IMPORT"
    elif isinstance(entity, JavaCompilationUnit):
        name = entity.fqn.split(".")[-1] if entity.fqn else Path(entity.path).stem
        full_path = entity.fqn or entity.path
        entity_type = "COMPILATION_UNIT"
    elif isinstance(entity, JavaPackage):
        name = entity.fqn.split(".")[-1]
        full_path = entity.fqn
        entity_type = "PACKAGE"
    elif isinstance(entity, JavaField):
        vb = getattr(entity, "variable_binding", None)
        if not vb:
            return None
        name = vb.name
        full_path = vb.fqn or name
        entity_type = entity.type
    elif isinstance(entity, (JavaEnumConstant, JavaRecordComponent)):
        name = entity.name
        full_path = entity.fqn or name
        entity_type = "ENUM_CONSTANT" if isinstance(entity, JavaEnumConstant) else "RECORD_COMPONENT"
    elif isinstance(entity, (FunctionLike, TypeDefinition)):
        name = entity.name
        full_path = entity.fqn
        entity_type = entity.type
    elif isinstance(entity, ControlFlowBlock):
        name = entity.branch
        entity_type = "CONTROL_FLOW_BLOCK"
        module_fqn = None
        if entity.parent_id and registry:
            module_fqn = _get_module_fqn_from_registry(entity.parent_id, registry)
        full_path = (
            f"{module_fqn}.__branch__.{entity.branch}.{entity.source_range.lineno}"
            if module_fqn
            else f"__branch__.{entity.branch}.{entity.source_range.lineno}"
        )
    elif isinstance(entity, ControlFlowGroup):
        name = entity.group_type
        entity_type = "CONTROL_FLOW_GROUP"
        module_fqn = None
        if entity.parent_id and registry:
            module_fqn = _get_module_fqn_from_registry(entity.parent_id, registry)
        full_path = (
            f"{module_fqn}.__group__.{entity.group_type}.{entity.source_range.lineno}"
            if module_fqn
            else f"__group__.{entity.group_type}.{entity.source_range.lineno}"
        )
    else:
        return None

    if not name or not full_path:
        return None

    metadata = {}
    sr = getattr(entity, "source_range", None)
    if sr:
        metadata["lineno"] = sr.lineno
        metadata["end_lineno"] = sr.end_lineno
        metadata["col_offset"] = sr.col_offset
        metadata["end_col_offset"] = sr.end_col_offset
        metadata["source_id"] = sr.source_id
    if isinstance(entity, JavaImport):
        metadata["import_path"] = entity.import_path
        metadata["import_kind"] = entity.import_kind
        metadata["imported_name"] = entity.imported_name
    fqn = getattr(entity, "fqn", None)
    if fqn:
        metadata["fqn"] = fqn
    if isinstance(entity, JavaCompilationUnit):
        if entity.package_fqn:
            metadata["package_fqn"] = entity.package_fqn
        if entity.module_name:
            metadata["module_name"] = entity.module_name
        metadata["path"] = entity.path
        metadata["import_stmt_ids"] = entity.import_stmt_ids
        metadata["type_ids"] = entity.type_ids
    if isinstance(entity, JavaPackage):
        metadata["subpackage_ids"] = entity.subpackage_ids
        metadata["compilation_unit_ids"] = entity.compilation_unit_ids
    path = getattr(entity, "path", None)
    if path is not None:
        metadata["path"] = path
    if isinstance(entity, TypeDefinition):
        if hasattr(entity, "visibility") and entity.visibility:
            metadata["visibility"] = entity.visibility
        if hasattr(entity, "annotations") and entity.annotations:
            metadata["annotations"] = [a.name for a in entity.annotations]
        if hasattr(entity, "docstring_range") and entity.docstring_range:
            dr = entity.docstring_range
            metadata["docstring_lineno"] = dr.lineno
            metadata["docstring_end_lineno"] = dr.end_lineno
        if hasattr(entity, "inner_type_ids") and entity.inner_type_ids:
            metadata["inner_type_ids"] = entity.inner_type_ids
    if isinstance(entity, JavaClass):
        if entity.superclass:
            metadata["superclass"] = entity.superclass
        if entity.implements:
            metadata["implements"] = entity.implements
        metadata["is_abstract"] = entity.is_abstract
        metadata["is_final"] = entity.is_final
        metadata["is_static"] = entity.is_static
        if entity.property_ids:
            metadata["property_ids"] = entity.property_ids
        if entity.method_ids:
            metadata["method_ids"] = entity.method_ids
    if isinstance(entity, JavaInterface):
        if entity.extends_interfaces:
            metadata["extends_interfaces"] = entity.extends_interfaces
        if entity.property_ids:
            metadata["property_ids"] = entity.property_ids
        if entity.method_ids:
            metadata["method_ids"] = entity.method_ids
    if isinstance(entity, JavaEnum):
        if entity.implements:
            metadata["implements"] = entity.implements
        metadata["enum_constant_ids"] = entity.enum_constant_ids
        if entity.property_ids:
            metadata["property_ids"] = entity.property_ids
        if entity.method_ids:
            metadata["method_ids"] = entity.method_ids
    if isinstance(entity, JavaRecord):
        if entity.implements:
            metadata["implements"] = entity.implements
        metadata["record_component_ids"] = entity.record_component_ids
        if entity.property_ids:
            metadata["property_ids"] = entity.property_ids
        if entity.method_ids:
            metadata["method_ids"] = entity.method_ids
    if isinstance(entity, JavaMethod):
        if entity.return_type:
            metadata["return_type"] = entity.return_type
        if entity.exceptions:
            metadata["exceptions"] = entity.exceptions
        metadata["is_abstract"] = entity.is_abstract
        metadata["is_final"] = entity.is_final
        metadata["is_static"] = entity.is_static
        metadata["is_default"] = entity.is_default
        metadata["is_synchronized"] = entity.is_synchronized
        metadata["is_native"] = entity.is_native
        if entity.annotations:
            metadata["annotations"] = [a.name for a in entity.annotations]
        if entity.docstring_range:
            dr = entity.docstring_range
            metadata["docstring_lineno"] = dr.lineno
            metadata["docstring_end_lineno"] = dr.end_lineno
        if hasattr(entity, "signature") and entity.signature:
            sig = entity.signature
            metadata["signature_lineno"] = sig.signature_range.lineno
            metadata["signature_end_lineno"] = sig.signature_range.end_lineno
            if sig.arguments_range:
                metadata["arguments_lineno"] = sig.arguments_range.lineno
                metadata["arguments_end_lineno"] = sig.arguments_range.end_lineno
            if sig.return_type_range:
                metadata["return_type_lineno"] = sig.return_type_range.lineno
                metadata["return_type_end_lineno"] = sig.return_type_range.end_lineno
    if isinstance(entity, JavaField):
        metadata["is_static"] = entity.is_static
        metadata["is_final"] = entity.is_final
        metadata["is_transient"] = entity.is_transient
        metadata["is_volatile"] = entity.is_volatile
    if isinstance(entity, JavaField):
        if hasattr(entity, "modifiers") and entity.modifiers:
            metadata["modifiers"] = entity.modifiers
        if hasattr(entity, "type_annotation") and entity.type_annotation:
            ta = entity.type_annotation
            metadata["type_annotation_lineno"] = ta.lineno
            metadata["type_annotation_end_lineno"] = ta.end_lineno
    if isinstance(entity, JavaRecordComponent):
        if entity.type_annotation:
            ta = entity.type_annotation
            metadata["type_annotation_lineno"] = ta.lineno
            metadata["type_annotation_end_lineno"] = ta.end_lineno
    if isinstance(entity, JavaEnumConstant) and entity.arguments_range:
        ar = entity.arguments_range
        metadata["arguments_lineno"] = ar.lineno
        metadata["arguments_end_lineno"] = ar.end_lineno
        metadata["arguments_col_offset"] = ar.col_offset
        metadata["arguments_end_col_offset"] = ar.end_col_offset
    if isinstance(entity, ControlFlowBlock):
        if entity.condition_range:
            cr = entity.condition_range
            metadata["condition_lineno"] = cr.lineno
            metadata["condition_end_lineno"] = cr.end_lineno
            metadata["condition_col_offset"] = cr.col_offset
            metadata["condition_end_col_offset"] = cr.end_col_offset
        metadata["import_stmt_ids"] = entity.import_stmt_ids
        metadata["type_ids"] = entity.type_ids
        metadata["function_ids"] = entity.function_ids
        metadata["variable_ids"] = entity.variable_ids
        metadata["nested_group_ids"] = entity.nested_group_ids
    if isinstance(entity, ControlFlowGroup):
        metadata["block_ids"] = entity.block_ids

    return {
        "id": entity.id,
        "language": language,
        "full_path": full_path,
        "name": name,
        "type": entity_type,
        "metadata_json": json.dumps(metadata, default=str),
        "parent_id": getattr(entity, "parent_id", None),
    }


def _get_module_fqn_from_registry(entity_id: str, registry: dict) -> str | None:
    seen: set[str] = set()
    current = entity_id
    while current and current not in seen:
        seen.add(current)
        entity = registry.get(current)
        if entity is None:
            break
        if hasattr(entity, "fqn") and entity.fqn:
            return entity.fqn
        current = getattr(entity, "parent_id", None)
    return None


def record_to_entity(record: dict) -> Entity | None:
    entity_class = TYPE_TO_CLASS.get(record["type"])
    if entity_class is None:
        return None
    meta = json.loads(record["metadata_json"])
    sr = SourceRange(
        lineno=meta.get("lineno", 0),
        end_lineno=meta.get("end_lineno", 0),
        col_offset=meta.get("col_offset", 0),
        end_col_offset=meta.get("end_col_offset", 0),
    )
    parent_id = record.get("parent_id") or meta.get("parent_id")

    if entity_class is JavaImport:
        return JavaImport(
            id=record["id"],
            parent_id=parent_id,
            import_path=meta.get("import_path", record["name"]),
            import_kind=meta.get("import_kind", ""),
            imported_name=meta.get("imported_name"),
            source_range=sr,
        )
    if entity_class is JavaCompilationUnit:
        return JavaCompilationUnit(
            id=record["id"],
            fqn=meta.get("fqn") or record["full_path"],
            package_fqn=meta.get("package_fqn"),
            module_name=meta.get("module_name"),
            path=meta.get("path", ""),
            source="",
            docstring_range=None,
            import_stmt_ids=meta.get("import_stmt_ids", []),
            type_ids=meta.get("type_ids", []),
        )
    if entity_class is JavaPackage:
        return JavaPackage(
            id=record["id"],
            parent_id=parent_id,
            path=meta.get("path", record["full_path"].replace(".", "/")),
            fqn=meta.get("fqn") or record["full_path"],
            subpackage_ids=meta.get("subpackage_ids", []),
            compilation_unit_ids=meta.get("compilation_unit_ids", []),
        )
    if entity_class in (
        JavaClass,
        JavaInterface,
        JavaEnum,
        JavaRecord,
        JavaAnnotationType,
    ):
        docstring_range = None
        if "docstring_lineno" in meta:
            docstring_range = SourceRange(
                lineno=meta["docstring_lineno"],
                end_lineno=meta["docstring_end_lineno"],
                col_offset=0,
                end_col_offset=0,
            )
        kwargs = {
            "id": record["id"],
            "parent_id": parent_id,
            "name": record["name"],
            "fqn": meta.get("fqn") or record["full_path"],
            "source_range": sr,
            "docstring_range": docstring_range,
            "annotations": [],
            "visibility": meta.get("visibility"),
            "inner_type_ids": meta.get("inner_type_ids", []),
            "method_ids": meta.get("method_ids", []),
            "property_ids": meta.get("property_ids", []),
        }
        if entity_class is JavaClass:
            return JavaClass(
                **kwargs,
                is_abstract=meta.get("is_abstract", False),
                is_final=meta.get("is_final", False),
                is_static=meta.get("is_static", False),
                superclass=meta.get("superclass"),
                implements=meta.get("implements", []),
            )
        if entity_class is JavaInterface:
            return JavaInterface(
                **kwargs,
                extends_interfaces=meta.get("extends_interfaces", []),
            )
        if entity_class is JavaEnum:
            return JavaEnum(
                **kwargs,
                implements=meta.get("implements", []),
                enum_constant_ids=meta.get("enum_constant_ids", []),
            )
        if entity_class is JavaRecord:
            return JavaRecord(
                **kwargs,
                implements=meta.get("implements", []),
                record_component_ids=meta.get("record_component_ids", []),
            )
        return JavaAnnotationType(**kwargs)
    if entity_class is JavaMethod:
        docstring_range = None
        if "docstring_lineno" in meta:
            docstring_range = SourceRange(
                lineno=meta["docstring_lineno"],
                end_lineno=meta["docstring_end_lineno"],
                col_offset=0,
                end_col_offset=0,
            )
        return JavaMethod(
            id=record["id"],
            parent_id=parent_id,
            name=record["name"],
            fqn=meta.get("fqn") or record["full_path"],
            type=record["type"],
            source_range=sr,
            docstring_range=docstring_range,
            signature=None,
            return_type=meta.get("return_type"),
            exceptions=meta.get("exceptions", []),
            is_abstract=meta.get("is_abstract", False),
            is_final=meta.get("is_final", False),
            is_static=meta.get("is_static", False),
            is_default=meta.get("is_default", False),
            is_synchronized=meta.get("is_synchronized", False),
            is_native=meta.get("is_native", False),
            annotations=[],
        )
    if entity_class is JavaField:
        return JavaField(
            id=record["id"],
            parent_id=parent_id,
            type=record["type"],
            source_range=sr,
            variable_binding=SimpleBinding(
                name=record["name"], fqn=meta.get("fqn") or record["full_path"]
            ),
            value_range=None,
            type_annotation=None,
            modifiers=meta.get("modifiers", []),
            is_static=meta.get("is_static", False),
            is_final=meta.get("is_final", False),
            is_transient=meta.get("is_transient", False),
            is_volatile=meta.get("is_volatile", False),
        )
    if entity_class is JavaEnumConstant:
        return JavaEnumConstant(
            id=record["id"],
            parent_id=parent_id,
            name=record["name"],
            fqn=meta.get("fqn") or record["full_path"],
            source_range=sr,
            arguments_range=_source_range_from_meta(meta, "arguments"),
        )
    if entity_class is JavaRecordComponent:
        return JavaRecordComponent(
            id=record["id"],
            parent_id=parent_id,
            name=record["name"],
            fqn=meta.get("fqn") or record["full_path"],
            source_range=sr,
            type_annotation=_source_range_from_meta(meta, "type_annotation"),
        )
    if entity_class is ControlFlowBlock:
        condition_range = None
        if "condition_lineno" in meta:
            condition_range = SourceRange(
                lineno=meta["condition_lineno"],
                end_lineno=meta["condition_end_lineno"],
                col_offset=meta["condition_col_offset"],
                end_col_offset=meta["condition_end_col_offset"],
            )
        return ControlFlowBlock(
            id=record["id"],
            parent_id=parent_id,
            branch=record["name"],
            source_range=sr,
            condition_range=condition_range,
            import_stmt_ids=meta.get("import_stmt_ids", []),
            type_ids=meta.get("type_ids", []),
            function_ids=meta.get("function_ids", []),
            variable_ids=meta.get("variable_ids", []),
            nested_group_ids=meta.get("nested_group_ids", []),
        )
    if entity_class is ControlFlowGroup:
        return ControlFlowGroup(
            id=record["id"],
            parent_id=parent_id,
            group_type=record["name"],
            source_range=sr,
            block_ids=meta.get("block_ids", []),
        )
    return None
