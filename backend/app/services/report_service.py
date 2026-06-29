"""Report service — scope-aware aggregations with no PII (AC-8.3).

Reuses _role_scoped from registro_service (Golden Rule: no duplication of
tenant/role scoping logic). Does NOT wrap admin_service.metrics — that
function returns a wider payload; this service is intentionally focused.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.dependencies import CampaignContext
from app.models.registro import Registro
from app.services.registro_service import _role_scoped


def por_seccion(db: Session, ctx: CampaignContext) -> dict:
    """Return a COUNT GROUP BY seccion report respecting role/tenant scope.

    Returns a dict compatible with SeccionReport schema:
      total: int
      items: list[{seccion: str, count: int}]

    PII guarantee: only seccion label + count are returned — no personal
    identifiers, no names, no contact details, no encrypted fields.
    """
    base = _role_scoped(ctx).subquery()
    reg = aliased(Registro, base)

    rows = db.execute(
        select(reg.seccion, func.count())
        .select_from(reg)
        .group_by(reg.seccion)
        .order_by(func.count().desc())
    ).all()

    items = [
        {"seccion": s or "Sin sección", "count": int(n)}
        for s, n in rows
    ]
    total = sum(i["count"] for i in items)

    return {"total": total, "items": items}
