from dataclasses import dataclass, field

from deproc.core.interfaces.parser.models import Node, SemanticContainer, SymbolID


@dataclass(kw_only=True)
class JavaPackage(SemanticContainer):
    path: str
    fqn: str
    subpackage_ids: list[SymbolID] = field(default_factory=list)
    compilation_unit_ids: list[SymbolID] = field(default_factory=list)
    package_info_id: SymbolID | None = None
    package_info_ids: list[SymbolID] = field(default_factory=list)

    @property
    def semantic_type(self) -> str:
        return "java.package"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.subpackage_ids = sorted(set(self.subpackage_ids))
        self.compilation_unit_ids = sorted(set(self.compilation_unit_ids))
        package_info_ids = set(self.package_info_ids)
        if self.package_info_id:
            package_info_ids.add(self.package_info_id)
        self.package_info_ids = sorted(package_info_ids)
        self.package_info_id = (
            self.package_info_ids[0] if self.package_info_ids else None
        )

    @property
    def contribution_ids(self) -> list[SymbolID]:
        return sorted(
            set(self.compilation_unit_ids)
            | set(self.subpackage_ids)
            | set(self.package_info_ids)
        )

    def _merge_contributions(self, other: SemanticContainer) -> None:
        if not isinstance(other, JavaPackage):
            raise ValueError("Java packages can only merge with Java packages")
        self.subpackage_ids = sorted(
            set(self.subpackage_ids) | set(other.subpackage_ids)
        )
        self.compilation_unit_ids = sorted(
            set(self.compilation_unit_ids) | set(other.compilation_unit_ids)
        )
        self.package_info_ids = sorted(
            set(self.package_info_ids) | set(other.package_info_ids)
        )
        self.package_info_id = (
            self.package_info_ids[0] if self.package_info_ids else None
        )


__all__ = [
    "JavaPackage",
    "Node",
    "SemanticContainer",
]
