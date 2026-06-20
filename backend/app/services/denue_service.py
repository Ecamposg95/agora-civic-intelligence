"""DENUE economic units reads — global-OR-own scope. GeoJSON uses lat/lon (dialect-independent)."""
from __future__ import annotations

from sqlalchemy import or_, select

from app.models.economic_unit import EconomicUnit


def _org_clause(org_id):
    """Global-OR-own scope: org_id=None returns only global rows; otherwise returns
    global rows (organization_id IS NULL) OR the tenant's own rows."""
    if org_id is None:
        return EconomicUnit.organization_id.is_(None)
    return or_(
        EconomicUnit.organization_id.is_(None),
        EconomicUnit.organization_id == org_id,
    )


def list_units(db, org_id, territory_code=None, actividad=None, limit=500):
    stmt = select(EconomicUnit).where(_org_clause(org_id))
    if territory_code:
        stmt = stmt.where(EconomicUnit.territory_code == territory_code)
    if actividad:
        stmt = stmt.where(EconomicUnit.actividad == actividad)
    rows = db.execute(stmt.limit(limit)).scalars().all()
    return [
        {
            "clave": r.clave,
            "nombre": r.nombre,
            "actividad": r.actividad,
            "estrato": r.estrato,
            "territory_code": r.territory_code,
            "lat": float(r.lat) if r.lat is not None else None,
            "lon": float(r.lon) if r.lon is not None else None,
        }
        for r in rows
    ]


def geojson(db, org_id, territory_code=None, limit=2000):
    """Point FeatureCollection. Uses lat/lon columns (dialect-independent)."""
    units = list_units(db, org_id, territory_code, None, limit)
    feats = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [u["lon"], u["lat"]]},
            "properties": {
                "clave": u["clave"],
                "nombre": u["nombre"],
                "actividad": u["actividad"],
                "estrato": u["estrato"],
            },
        }
        for u in units
        if u["lon"] is not None and u["lat"] is not None
    ]
    return {"type": "FeatureCollection", "features": feats}
