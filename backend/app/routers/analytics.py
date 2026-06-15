"""Analytics router — civic intelligence overview metrics."""

from typing import Any

from fastapi import APIRouter

from app.dependencies import Tenant
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", summary="Civic intelligence overview")
def overview(ctx: Tenant) -> dict[str, Any]:
    """Return high-level KPIs and trend series for the executive dashboard."""
    return analytics_service.get_overview(ctx.organization_id)
