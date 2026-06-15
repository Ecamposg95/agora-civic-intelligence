"""Analytics router — civic intelligence overview metrics."""

from typing import Any

from fastapi import APIRouter

from app.dependencies import DbSession, Tenant
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", summary="Civic intelligence overview")
def overview(ctx: Tenant, db: DbSession) -> dict[str, Any]:
    """Return real, tenant-scoped KPIs, coverage and activity for the dashboard."""
    return analytics_service.get_overview(db, ctx)
