"""Analytics service — civic intelligence aggregates.

All metrics are computed from the live database and are tenant-scoped:
superadmins see platform-wide totals, everyone else sees only their
organization. No values are fabricated — fields we don't yet have a data
pipeline for (e.g. padrón/turnout) are simply not reported.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import TenantContext
from app.integrations.ine import config as ine_config
from app.models.audit_log import AuditLog
from app.models.electoral_area import ElectoralArea
from app.models.organization import Organization
from app.models.user import User

ACTIVITY_WINDOW_DAYS = 14


def get_overview(db: Session, ctx: TenantContext) -> dict[str, Any]:
    """Return high-level KPIs, territorial coverage, an activity trend and
    governance alerts — all derived from real, tenant-scoped data."""

    # --- Summary KPIs -------------------------------------------------------
    areas_stmt = select(func.count(ElectoralArea.id))
    users_stmt = select(func.count(User.id)).where(User.is_active.is_(True))
    if not ctx.is_superadmin:
        areas_stmt = areas_stmt.where(
            ElectoralArea.organization_id == ctx.organization_id
        )
        users_stmt = users_stmt.where(User.organization_id == ctx.organization_id)

    electoral_areas = int(db.execute(areas_stmt).scalar_one())
    active_users = int(db.execute(users_stmt).scalar_one())

    if ctx.is_superadmin:
        organizations = int(db.execute(select(func.count(Organization.id))).scalar_one())
    else:
        organizations = 1

    data_sources = len(ine_config.SOURCES)

    # --- Territorial coverage (areas by level) ------------------------------
    cov_stmt = select(ElectoralArea.level, func.count(ElectoralArea.id))
    if not ctx.is_superadmin:
        cov_stmt = cov_stmt.where(
            ElectoralArea.organization_id == ctx.organization_id
        )
    cov_stmt = cov_stmt.group_by(ElectoralArea.level)
    coverage = [
        {"level": getattr(level, "value", str(level)), "count": int(count)}
        for level, count in db.execute(cov_stmt).all()
    ]
    coverage.sort(key=lambda c: c["count"], reverse=True)

    # --- Activity trend: audit events per day over the window ---------------
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=ACTIVITY_WINDOW_DAYS - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    act_stmt = select(AuditLog.created_at).where(AuditLog.created_at >= start)
    if not ctx.is_superadmin:
        act_stmt = act_stmt.where(AuditLog.organization_id == ctx.organization_id)

    buckets: dict[str, int] = {
        (start + timedelta(days=i)).date().isoformat(): 0
        for i in range(ACTIVITY_WINDOW_DAYS)
    }
    total_events = 0
    for created_at in db.execute(act_stmt).scalars().all():
        total_events += 1
        key = created_at.date().isoformat()
        if key in buckets:
            buckets[key] += 1
    # period as MM-DD for a compact axis label
    activity = [{"period": day[5:], "value": count} for day, count in buckets.items()]

    # --- Governance alerts derived from real state --------------------------
    alerts: list[dict[str, str]] = []
    if electoral_areas == 0:
        alerts.append(
            {
                "level": "warning",
                "title": "Sin cartografía cargada",
                "detail": "Ingesta el Marco Geográfico Electoral para poblar el "
                "mapa y la cobertura territorial.",
            }
        )
    else:
        levels = len(coverage)
        alerts.append(
            {
                "level": "info",
                "title": "Cobertura territorial activa",
                "detail": f"{electoral_areas} áreas electorales en {levels} "
                f"nivel{'es' if levels != 1 else ''}.",
            }
        )
    alerts.append(
        {
            "level": "info",
            "title": "Bitácora de auditoría activa",
            "detail": f"{total_events} eventos registrados en los últimos "
            f"{ACTIVITY_WINDOW_DAYS} días.",
        }
    )

    return {
        "summary": {
            "electoral_areas": electoral_areas,
            "organizations": organizations,
            "users": active_users,
            "data_sources": data_sources,
        },
        "coverage": coverage,
        "trends": {"activity": activity},
        "alerts": alerts,
        "generated_at": now.isoformat(),
    }
