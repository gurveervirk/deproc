from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _normalize_path(self.path))
        object.__setattr__(self, "kind", self.kind.strip().lower())
        object.__setattr__(self, "provenance", self.provenance.strip().lower())


@dataclass(frozen=True)
class AnalysisScope:
    roots: tuple[RootDescriptor, ...] = ()
    selected_languages: frozenset[str] = frozenset()
    selected_file_extensions: frozenset[str] = frozenset()
    exclusions: frozenset[str] = frozenset()

    def __init__(
        self,
        project_roots: Iterable[str | RootDescriptor] = (),
        source_roots: Iterable[str | RootDescriptor] = (),
        declaration_roots: Iterable[str | RootDescriptor] = (),
        dependency_roots: Iterable[str | RootDescriptor] = (),
        *,
        roots: Iterable[str | RootDescriptor] = (),
        selected_languages: Iterable[str] = (),
        selected_file_extensions: Iterable[str] = (),
        exclusions: Iterable[str] = (),
    ) -> None:
        descriptors: list[RootDescriptor] = []
        for kind, paths in (
            ("project", project_roots),
            ("source", source_roots),
            ("declaration", declaration_roots),
            ("dependency", dependency_roots),
        ):
            descriptors.extend(
                RootDescriptor(item.path, kind, item.provenance)
                if isinstance(item, RootDescriptor)
                else RootDescriptor(item, kind)
                for item in paths
            )
        descriptors.extend(
            item if isinstance(item, RootDescriptor) else RootDescriptor(item)
            for item in roots
        )
        object.__setattr__(self, "roots", tuple(descriptors))
        object.__setattr__(
            self,
            "selected_languages",
            frozenset(language.strip().lower() for language in selected_languages),
        )
        object.__setattr__(
            self,
            "selected_file_extensions",
            _normalize_extensions(selected_file_extensions),
        )
        object.__setattr__(self, "exclusions", frozenset(exclusions))

    @property
    def project_roots(self) -> tuple[RootDescriptor, ...]:
        return tuple(root for root in self.roots if root.kind == "project")

    @property
    def source_roots(self) -> tuple[RootDescriptor, ...]:
        return tuple(root for root in self.roots if root.kind == "source")

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


__all__ = ["AnalysisScope", "DiscoveredFile", "RootDescriptor"]
