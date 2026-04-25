from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExternalEntityRef(BaseModel):
    name: str
    type: str = "UNKNOWN"
    version: str | None = None
    content_hash: str | None = None
    alias: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    name: str
    type: str = "UNKNOWN"
    labels: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""
    language: str = "unknown"


class Relationship(BaseModel):
    from_entity: Entity
    to_entity: Entity | ExternalEntityRef
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relationship] = Field(default_factory=list)
    other_relations: dict[str, list[tuple[str, ExternalEntityRef]]] = Field(
        default_factory=dict
    )
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    symbol_maps: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    alias_hops: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)

