"""Schemas for the external data-source surface (/api/sources, WMS layers)."""

from typing import Any

from pydantic import BaseModel


class SourceInfo(BaseModel):
    """A consumable external data source."""

    id: str
    name: str
    kind: str
    base_url: str
    formats: list[str]
    auth_required: bool
    notes: str


class DatasetSummary(BaseModel):
    """A condensed CKAN dataset entry."""

    id: str
    title: str
    organization: str | None = None
    formats: list[str] = []
    url: str | None = None


class WmsLayer(BaseModel):
    """A MapLibre-ready WMS raster layer descriptor."""

    id: str
    name: str
    level: str
    type: str = "raster"
    tiles: list[str]
    tileSize: int = 256
    srid: int = 4326


class CandidaturasResponse(BaseModel):
    """Opaque pass-through wrapper for Candidaturas MX payloads."""

    source: str = "candidaturas_mx"
    data: Any
