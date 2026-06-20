"""DENUE economic units — list and GeoJSON endpoints."""
from typing import Any

from fastapi import APIRouter, Query

from app.dependencies import DbSession, Tenant
from app.services import denue_service

router = APIRouter(prefix="/denue", tags=["denue"])


@router.get("", summary="List economic units")
def list_units(
    db: DbSession,
    ctx: Tenant,
    territory_code: str | None = Query(None),
    actividad: str | None = Query(None),
    limit: int = Query(500, le=5000),
) -> dict[str, Any]:
    return {
        "units": denue_service.list_units(
            db, ctx.organization_id, territory_code, actividad, limit
        )
    }


@router.get("/geojson", summary="Economic units as GeoJSON points")
def geojson(
    db: DbSession,
    ctx: Tenant,
    territory_code: str | None = Query(None),
    limit: int = Query(2000, le=10000),
) -> dict[str, Any]:
    return denue_service.geojson(db, ctx.organization_id, territory_code, limit)
