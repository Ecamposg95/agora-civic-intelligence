"""Resolve fact rows' area_id by matching territory_code -> electoral_areas.code."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.models.electoral_area import ElectoralArea


@dataclass
class ResolveResult:
    matched: int
    unmatched: int


def resolve_area_ids(db, fact_model, level_map) -> ResolveResult:
    """For fact rows where area_id IS NULL, set area_id to the global
    electoral_areas row whose code == territory_code at the level mapped from
    the fact's `nivel`. Returns matched/unmatched counts. Never fabricates."""
    rows = db.execute(select(fact_model).where(fact_model.area_id.is_(None))).scalars().all()
    matched = unmatched = 0
    cache: dict[tuple, str | None] = {}
    for r in rows:
        level = level_map.get(r.nivel)
        if level is None:
            unmatched += 1
            continue
        key = (level, r.territory_code)
        if key not in cache:
            area = db.execute(
                select(ElectoralArea).where(
                    ElectoralArea.organization_id.is_(None),
                    ElectoralArea.level == level,
                    ElectoralArea.code == r.territory_code,
                )
            ).scalars().first()
            cache[key] = area.id if area else None
        area_id = cache[key]
        if area_id:
            r.area_id = area_id
            matched += 1
        else:
            unmatched += 1
    db.commit()
    return ResolveResult(matched=matched, unmatched=unmatched)
