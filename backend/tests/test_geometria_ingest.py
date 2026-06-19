from pathlib import Path
from app.ingestion.engine import run_ingest
from app.ingestion.datasets import DATASETS
from app.models.electoral_area import ElectoralArea, AreaLevel
from app.models.ingestion import IngestRun
from tests.conftest import TestingSessionLocal
FIX = Path(__file__).parent / "fixtures"


class _Ctx:
    organization_id = None
    campaign_id = None
    is_superadmin = True
    class user:  # noqa
        id = "tester"


def test_geometria_ingest_creates_global_areas():
    db = TestingSessionLocal()
    try:
        spec = DATASETS["geometria"]
        res = run_ingest(db, _Ctx(), spec, FIX / "areas_min.geojson", source=None,
                         extra={"level": "distrito_federal", "name_prop": "NOMBRE", "code_prop": "CLAVE"}, replace=True)
        assert res.inserted == 1
        a = db.query(ElectoralArea).filter(ElectoralArea.code == "0901").one()
        assert a.level == AreaLevel.DISTRITO_FEDERAL
        assert a.organization_id is None
        assert a.geometry is not None          # GeoJSON text on sqlite
        assert a.ingest_run_id == res.run_id   # traceable
        assert a.name == "Distrito 01"
    finally:
        db.query(ElectoralArea).delete(); db.query(IngestRun).delete(); db.commit(); db.close()


def test_geometria_replace_by_level_idempotent():
    db = TestingSessionLocal()
    try:
        spec = DATASETS["geometria"]
        ex = {"level": "distrito_federal", "name_prop": "NOMBRE", "code_prop": "CLAVE"}
        run_ingest(db, _Ctx(), spec, FIX / "areas_min.geojson", source=None, extra=ex, replace=True)
        run_ingest(db, _Ctx(), spec, FIX / "areas_min.geojson", source=None, extra=ex, replace=True)
        assert db.query(ElectoralArea).filter(ElectoralArea.level == AreaLevel.DISTRITO_FEDERAL).count() == 1
    finally:
        db.query(ElectoralArea).delete(); db.query(IngestRun).delete(); db.commit(); db.close()
