"""Maps router — layer catalog, tenant-scoped GeoJSON areas, and WMS layers."""

from typing import Any

from fastapi import APIRouter, Query

from app.dependencies import DbSession, Tenant
from app.integrations.ine import cartografia
from app.services import map_service

router = APIRouter(prefix="/maps", tags=["maps"])


@router.get("/layers", summary="List available map layers")
def list_layers() -> dict[str, Any]:
    """Return the catalog of map layers available to the explorer."""
    return {"layers": map_service.list_layers()}


# Default simplification tolerance (SRID 4326 degrees) per level. Dense layers
# (municipios) are simplified hard; sparse layers (states) are left crisp.
_DEFAULT_SIMPLIFY: dict[str, float] = {
    "municipality": 0.01,
    "district": 0.005,
}


@router.get("/areas", summary="Electoral areas as GeoJSON")
def list_areas(
    db: DbSession,
    ctx: Tenant,
    level: str | None = Query(
        None, description="Filter by level (e.g. state, district)"
    ),
    simplify: float | None = Query(
        None, ge=0, le=1,
        description="Geometry simplification tolerance (degrees). Omit for the "
        "per-level default; 0 disables.",
    ),
) -> dict[str, Any]:
    """Return tenant-scoped electoral areas as a GeoJSON FeatureCollection."""
    tol = simplify if simplify is not None else _DEFAULT_SIMPLIFY.get(level or "", 0.0)
    return map_service.list_areas_geojson(db, ctx.organization_id, level, tol)


@router.get("/wms-layers", summary="INE SIGE WMS layers for the basemap")
def wms_layers(ctx: Tenant) -> dict[str, Any]:
    """Return MapLibre-ready SIGE WMS layer descriptors (empty if unconfigured)."""
    return {"configured": cartografia.wms_configured(), "layers": cartografia.wms_layers()}
