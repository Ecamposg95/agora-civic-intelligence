"""Election results — reads + derived metrics."""
from typing import Any

from fastapi import APIRouter, Query

from app.dependencies import DbSession, Tenant
from app.services import resultados_service

router = APIRouter(prefix="/resultados", tags=["resultados"])


@router.get("", summary="List election results")
def list_results(
    db: DbSession,
    ctx: Tenant,
    anio: int | None = Query(None),
    nivel: str | None = Query(None),
    territory_code: str | None = Query(None),
    eleccion: str | None = Query(None),
) -> dict[str, Any]:
    return {
        "results": resultados_service.list_results(
            db, ctx.organization_id, anio, nivel, territory_code, eleccion
        )
    }


@router.get("/derived", summary="Derived participation/abstention/margin for a territory")
def derived(
    db: DbSession,
    ctx: Tenant,
    anio: int = Query(...),
    nivel: str = Query(...),
    territory_code: str = Query(...),
    eleccion: str = Query(...),
) -> dict[str, Any]:
    return resultados_service.derived(
        db, ctx.organization_id, anio, nivel, territory_code, eleccion
    )
