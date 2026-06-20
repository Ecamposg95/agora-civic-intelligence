"""Socioeconomic metrics — read endpoint."""
from typing import Any

from fastapi import APIRouter, Query

from app.dependencies import DbSession, Tenant
from app.services import socio_service

router = APIRouter(prefix="/socio", tags=["socio"])


@router.get("", summary="List socioeconomic metrics")
def list_metrics(
    db: DbSession,
    ctx: Tenant,
    anio: int | None = Query(None),
    nivel: str | None = Query(None),
    territory_code: str | None = Query(None),
    indicador: str | None = Query(None),
) -> dict[str, Any]:
    return {
        "metrics": socio_service.list_metrics(
            db, ctx.organization_id, anio, nivel, territory_code, indicador
        )
    }
