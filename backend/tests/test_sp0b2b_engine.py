import types, tempfile, os
from tests.conftest import TestingSessionLocal
from app.ingestion.datasets import DATASETS
from app.ingestion.engine import run_ingest
from app.ingestion.resolve import resolve_area_ids
from app.models.election_result import ElectionResult
from app.models.electoral_area import ElectoralArea, AreaLevel


def _ctx():
    return types.SimpleNamespace(organization_id=None, campaign_id=None,
                                 user=types.SimpleNamespace(id="t"))


def _csv(text):
    fd, p = tempfile.mkstemp(suffix=".csv"); os.write(fd, text.encode()); os.close(fd)
    return p


def test_ingest_resultados_and_resolve_area_id():
    db = TestingSessionLocal()
    try:
        db.query(ElectionResult).delete(); db.query(ElectoralArea).delete()
        db.add(ElectoralArea(organization_id=None, level=AreaLevel.MUNICIPIO,
                             code="15001", name="Toluca"))
        db.commit()
        path = _csv("nivel,clave,partido,votos\nmunicipio,15001,MORENA,1234\nmunicipio,15001,PAN,900\n")
        res = run_ingest(db, _ctx(), DATASETS["resultados"], path, source=None,
                         extra={"anio": 2021, "eleccion": "ayuntamiento"})
        assert res.status == "success" and res.inserted == 2
        rr = resolve_area_ids(db, ElectionResult, {"municipio": AreaLevel.MUNICIPIO})
        assert rr.matched == 2 and rr.unmatched == 0
        assert all(r.area_id is not None for r in db.query(ElectionResult).all())
    finally:
        os.remove(path)
        db.query(ElectionResult).delete()
        db.query(ElectoralArea).delete()
        db.commit()
        db.close()
