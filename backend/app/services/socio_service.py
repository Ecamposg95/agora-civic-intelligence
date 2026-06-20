"""Socioeconomic metrics reads — global-OR-own scope."""
from __future__ import annotations

from sqlalchemy import or_, select

from app.models.socio import SocioMetric


def _org_clause(org_id):
    """Global-OR-own scope: org_id=None returns only global rows; otherwise returns
    global rows (organization_id IS NULL) OR the tenant's own rows."""
    if org_id is None:
        return SocioMetric.organization_id.is_(None)
    return or_(
        SocioMetric.organization_id.is_(None),
        SocioMetric.organization_id == org_id,
    )


def list_metrics(db, org_id, anio=None, nivel=None, territory_code=None, indicador=None):
    stmt = select(SocioMetric).where(_org_clause(org_id))
    if anio is not None:
        stmt = stmt.where(SocioMetric.anio == anio)
    if nivel:
        stmt = stmt.where(SocioMetric.nivel == nivel)
    if territory_code:
        stmt = stmt.where(SocioMetric.territory_code == territory_code)
    if indicador:
        stmt = stmt.where(SocioMetric.indicador == indicador)
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "territory_code": r.territory_code,
            "nivel": r.nivel,
            "anio": r.anio,
            "indicador": r.indicador,
            "valor": float(r.valor),
        }
        for r in rows
    ]
