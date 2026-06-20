"""Election-results reads + query-time derived metrics (never stored)."""
from __future__ import annotations

from sqlalchemy import or_, select

from app.models.election_result import ElectionResult

SENTINELS = {"_LISTA_NOMINAL", "_TOTAL", "_NULOS", "_NO_REGISTRADAS"}


def _org_clause(org_id):
    """Global-OR-own scope: org_id=None returns only global rows; otherwise returns
    global rows (organization_id IS NULL) OR the tenant's own rows."""
    if org_id is None:
        return ElectionResult.organization_id.is_(None)
    return or_(
        ElectionResult.organization_id.is_(None),
        ElectionResult.organization_id == org_id,
    )


def list_results(db, org_id, anio=None, nivel=None, territory_code=None, eleccion=None):
    stmt = select(ElectionResult).where(_org_clause(org_id))
    if anio is not None:
        stmt = stmt.where(ElectionResult.anio == anio)
    if nivel:
        stmt = stmt.where(ElectionResult.nivel == nivel)
    if territory_code:
        stmt = stmt.where(ElectionResult.territory_code == territory_code)
    if eleccion:
        stmt = stmt.where(ElectionResult.eleccion == eleccion)
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "territory_code": r.territory_code,
            "nivel": r.nivel,
            "anio": r.anio,
            "eleccion": r.eleccion,
            "partido": r.partido,
            "votos": float(r.votos),
        }
        for r in rows
    ]


def derived(db, org_id, anio, nivel, territory_code, eleccion):
    rows = db.execute(
        select(ElectionResult).where(
            _org_clause(org_id),
            ElectionResult.anio == anio,
            ElectionResult.nivel == nivel,
            ElectionResult.territory_code == territory_code,
            ElectionResult.eleccion == eleccion,
        )
    ).scalars().all()
    parties = {r.partido: float(r.votos) for r in rows}
    lista_nominal = parties.get("_LISTA_NOMINAL")
    nulos = parties.get("_NULOS", 0.0)
    real = {p: v for p, v in parties.items() if p not in SENTINELS}
    total_real = sum(real.values())
    total_votos = total_real + nulos
    ordered = sorted(real.items(), key=lambda kv: kv[1], reverse=True)
    ganador = ordered[0][0] if ordered else None
    top1 = ordered[0][1] if ordered else 0.0
    top2 = ordered[1][1] if len(ordered) > 1 else 0.0
    participacion = (total_votos / lista_nominal) if lista_nominal else None
    return {
        "territory_code": territory_code,
        "anio": anio,
        "eleccion": eleccion,
        "lista_nominal": lista_nominal,
        "total_votos": total_votos,
        "participacion": participacion,
        "abstencion": (1 - participacion) if participacion is not None else None,
        "ganador": ganador,
        "margen": ((top1 - top2) / total_real) if total_real else None,
    }
