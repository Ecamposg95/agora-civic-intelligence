import importlib, importlib.util, tempfile, os, sys
from pathlib import Path

from tests.conftest import TestingSessionLocal
from app.models.ingestion import DataSource, IngestRun
from app.models.socio import SocioMetric


def _load_cli():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "ingest_file", root / "scripts" / "ingest_file.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _csv(text, suffix=".csv"):
    fd, p = tempfile.mkstemp(suffix=suffix)
    os.write(fd, text.encode())
    os.close(fd)
    return p


def test_cli_ingest_socio_importable(monkeypatch):
    ingest_file = _load_cli()
    monkeypatch.setattr(ingest_file, "SessionLocal", TestingSessionLocal, raising=False)
    path = _csv("nivel,clave,indicador,valor\nmunicipio,15001,pobreza,0.3\n")
    try:
        res = ingest_file.ingest(dataset="socio", file=path, source="CONEVAL",
                                 org=None, campaign=None, extra={"anio": 2020}, replace=False)
        assert res.status in ("success", "partial")
        assert res.inserted == 1
    finally:
        db = TestingSessionLocal()
        db.query(SocioMetric).delete()
        db.query(IngestRun).delete()
        db.query(DataSource).filter(DataSource.name == "CONEVAL").delete()
        db.commit()
        db.close()
        os.remove(path)
