from app.ingestion.resolve import resolve_area_ids
from app.models.electoral_area import ElectoralArea, AreaLevel
from app.models.census import CensusMetric
from tests.conftest import TestingSessionLocal


def test_resolve_sets_area_id_on_match():
    db = TestingSessionLocal()
    try:
        area = ElectoralArea(name="Edomex", level=AreaLevel.ESTADO, code="15", organization_id=None)
        db.add(area); db.flush()
        m1 = CensusMetric(organization_id=None, anio=2020, nivel="estado", territory_code="15", indicador="POBTOT", valor=1)
        m2 = CensusMetric(organization_id=None, anio=2020, nivel="estado", territory_code="99", indicador="POBTOT", valor=2)
        db.add_all([m1, m2]); db.commit()
        result = resolve_area_ids(db, CensusMetric, {"estado": AreaLevel.ESTADO})
        db.refresh(m1); db.refresh(m2)
        assert m1.area_id == area.id and m2.area_id is None
        assert result.matched == 1 and result.unmatched == 1
    finally:
        db.query(CensusMetric).delete(); db.query(ElectoralArea).delete(); db.commit(); db.close()


def test_resolve_skips_already_resolved():
    db = TestingSessionLocal()
    try:
        area = ElectoralArea(name="Edomex", level=AreaLevel.ESTADO, code="15", organization_id=None)
        db.add(area); db.flush()
        m = CensusMetric(organization_id=None, anio=2020, nivel="estado", territory_code="15", indicador="X", valor=1, area_id="preset")
        db.add(m); db.commit()
        result = resolve_area_ids(db, CensusMetric, {"estado": AreaLevel.ESTADO})
        db.refresh(m)
        assert m.area_id == "preset"  # untouched (was not NULL)
        assert result.matched == 0 and result.unmatched == 0  # only NULL rows considered
    finally:
        db.query(CensusMetric).delete(); db.query(ElectoralArea).delete(); db.commit(); db.close()
