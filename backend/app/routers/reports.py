"""Reports router — /reports/* aggregated views, RBAC-gated, no PII (AC-8.3)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import AdminCtx, DbSession, require_roles
from app.models.user import UserRole
from app.schemas.report import SeccionReport
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])

# admin + lider may access reports; activista/viewer excluded.
# Superadmin always passes (handled inside require_roles).
ReportsCtx = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.LIDER))]


@router.get("/secciones", response_model=SeccionReport)
def secciones_report(
    db: DbSession,
    ctx: AdminCtx,
    _perm: ReportsCtx,
) -> SeccionReport:
    """Return COUNT GROUP BY seccion within the caller's role/tenant scope.

    - ADMIN → full campaign scope.
    - LIDER → only their estructura's registros.
    - SUPERADMIN (no X-Campaign-Id) → consolidated cross-tenant view.
    No PII is returned: each item contains only `seccion` + `count`.
    """
    return SeccionReport(**report_service.por_seccion(db, ctx))
