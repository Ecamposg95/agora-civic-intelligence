"""Orchestration for INE data ingestion.

Currently focused on loading Marco Geográfico Electoral GeoJSON into the
tenant-scoped ``electoral_areas`` table (PostGIS). Geometry is inserted via
``ST_GeomFromGeoJSON`` so no Python geometry deps are required.
"""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.integrations.ine import config
from app.models.electoral_area import AreaLevel, ElectoralArea
from app.services.audit_service import record_audit


def _feature_geometry_expr(geometry: dict[str, Any] | None):
    """Build a PostGIS geometry SQL expression (SRID 4326) from GeoJSON."""
    if not geometry:
        return None
    import json

    return func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(geometry)), 4326)


def ingest_geojson_areas(
    db: Session,
    *,
    organization_id: str,
    features: Iterable[dict[str, Any]],
    level: AreaLevel | str = AreaLevel.DISTRICT,
    name_prop: str = "name",
    code_prop: str | None = "code",
    actor_id: str | None = None,
    commit: bool = True,
) -> int:
    """Insert GeoJSON features as ElectoralArea rows for a tenant.

    Returns the number of areas inserted. ``level`` may be an AreaLevel or an
    INE level name (mapped via ``config.map_level``).
    """
    resolved_level = level if isinstance(level, AreaLevel) else config.map_level(level)

    inserted = 0
    for feature in features:
        props: dict[str, Any] = feature.get("properties") or {}
        name = str(props.get(name_prop) or props.get("NOMBRE") or "Sin nombre")
        code = None
        if code_prop:
            raw_code = props.get(code_prop) or props.get("CLAVE") or props.get("CVE")
            code = str(raw_code) if raw_code is not None else None

        area = ElectoralArea(
            organization_id=organization_id,
            name=name,
            code=code,
            level=resolved_level,
            created_by=actor_id,
            updated_by=actor_id,
        )
        geom_expr = _feature_geometry_expr(feature.get("geometry"))
        if geom_expr is not None:
            area.geometry = geom_expr
        db.add(area)
        inserted += 1

    record_audit(
        db,
        action="ine.ingest.cartografia",
        actor_id=actor_id,
        organization_id=organization_id,
        entity_type="electoral_area",
        meta={"inserted": inserted, "level": resolved_level.value},
    )

    if commit:
        db.commit()
    return inserted


def ingest_feature_collection(
    db: Session,
    *,
    organization_id: str,
    feature_collection: dict[str, Any],
    level: AreaLevel | str = AreaLevel.DISTRICT,
    name_prop: str = "name",
    code_prop: str | None = "code",
    actor_id: str | None = None,
    commit: bool = True,
) -> int:
    """Ingest a GeoJSON FeatureCollection dict."""
    features = feature_collection.get("features", [])
    return ingest_geojson_areas(
        db,
        organization_id=organization_id,
        features=features,
        level=level,
        name_prop=name_prop,
        code_prop=code_prop,
        actor_id=actor_id,
        commit=commit,
    )
