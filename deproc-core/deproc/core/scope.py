from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from hashlib import sha256


def _normalize_path(path: str) -> str:
    return os.path.abspath(os.path.normpath(os.fspath(path)))


def _normalize_extensions(extensions: Iterable[str]) -> frozenset[str]:
    return frozenset(
        extension if extension.startswith(".") else f".{extension}"
        for extension in (item.strip().lower() for item in extensions)
    )


@dataclass(frozen=True)
class RootDescriptor:
    path: str
    kind: str = "project"
    provenance: str = "explicit"
    root_id: str | None = None

    def __post_init__(self) -> None:
        normalized_path = _normalize_path(self.path)
        normalized_kind = self.kind.strip().lower()
        normalized_provenance = self.provenance.strip().lower()
        object.__setattr__(self, "path", normalized_path)
        object.__setattr__(self, "kind", normalized_kind)
        object.__setattr__(self, "provenance", normalized_provenance)
        if self.root_id is None or not self.root_id.strip():
            digest = sha256(
                f"{normalized_kind}\0{normalized_path}".encode()
            ).hexdigest()[:16]
            object.__setattr__(self, "root_id", f"{normalized_kind}-{digest}")
        else:
            object.__setattr__(self, "root_id", self.root_id.strip())


@dataclass(frozen=True)
class AnalysisScope:
    roots: tuple[RootDescriptor, ...] = ()
    selected_languages: frozenset[str] = frozenset()
    selected_file_extensions: frozenset[str] = frozenset()
    exclusions: frozenset[str] = frozenset()
    language_selection_explicit: bool = field(init=False)
    file_extension_selection_explicit: bool = field(init=False)

    def __init__(
        self,
        project_roots: Iterable[str | RootDescriptor] = (),
        source_roots: Iterable[str | RootDescriptor] = (),
        generated_roots: Iterable[str | RootDescriptor] = (),
        declaration_roots: Iterable[str | RootDescriptor] = (),
        dependency_roots: Iterable[str | RootDescriptor] = (),
        *,
        roots: Iterable[str | RootDescriptor] = (),
        selected_languages: Iterable[str] | None = None,
        selected_file_extensions: Iterable[str] | None = None,
        exclusions: Iterable[str] = (),
    ) -> None:
        descriptors: list[RootDescriptor] = []

        def descriptor(item: str | RootDescriptor, kind: str) -> RootDescriptor:
            if isinstance(item, RootDescriptor):
                return RootDescriptor(
                    item.path,
                    kind,
                    item.provenance,
                    item.root_id,
                )
            return RootDescriptor(item, kind)

        for kind, paths in (
            ("project", project_roots),
            ("source", source_roots),
            ("generated", generated_roots),
            ("declaration", declaration_roots),
            ("dependency", dependency_roots),
        ):
            descriptors.extend(descriptor(item, kind) for item in paths)
        descriptors.extend(
            item if isinstance(item, RootDescriptor) else RootDescriptor(item)
            for item in roots
        )
        object.__setattr__(self, "roots", tuple(descriptors))
        object.__setattr__(
            self, "language_selection_explicit", selected_languages is not None
        )
        object.__setattr__(
            self,
            "file_extension_selection_explicit",
            selected_file_extensions is not None,
        )
        object.__setattr__(
            self,
            "selected_languages",
            frozenset(
                language.strip().lower() for language in (selected_languages or ())
            ),
        )
        object.__setattr__(
            self,
            "selected_file_extensions",
            _normalize_extensions(selected_file_extensions or ()),
        )
        object.__setattr__(self, "exclusions", frozenset(exclusions))

    @property
    def project_roots(self) -> tuple[RootDescriptor, ...]:
        return tuple(root for root in self.roots if root.kind == "project")

    @property
    def source_roots(self) -> tuple[RootDescriptor, ...]:
        return tuple(root for root in self.roots if root.kind == "source")

    @property
    def generated_roots(self) -> tuple[RootDescriptor, ...]:
        return tuple(root for root in self.roots if root.kind == "generated")

    @property
    def declaration_roots(self) -> tuple[RootDescriptor, ...]:
        return tuple(root for root in self.roots if root.kind == "declaration")

    @property
    def dependency_roots(self) -> tuple[RootDescriptor, ...]:
        return tuple(root for root in self.roots if root.kind == "dependency")


@dataclass(frozen=True)
class DiscoveredFile:
    path: str
    root: RootDescriptor

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _normalize_path(self.path))

    @property
    def provenance(self) -> str:
        return self.root.provenance

    @property
    def root_kind(self) -> str:
        return self.root.kind

    @property
    def root_id(self) -> str:
        return self.root.root_id or ""

    @property
    def relative_path(self) -> str:
        return os.path.relpath(self.path, self.root.path).replace(os.sep, "/")


__all__ = ["AnalysisScope", "DiscoveredFile", "RootDescriptor"]
