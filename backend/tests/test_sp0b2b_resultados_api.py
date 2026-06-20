"""Tests for resultados_service (derived metrics math) + /api/resultados router."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.election_result import ElectionResult
from app.services import resultados_service
from tests.conftest import TestingSessionLocal, auth_headers


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _seed(db):
    db.query(ElectionResult).delete()
    rows = [("MORENA", 600), ("PAN", 300), ("_NULOS", 20), ("_LISTA_NOMINAL", 1000)]
    for partido, votos in rows:
        db.add(
            ElectionResult(
                organization_id=None,
                anio=2021,
                nivel="municipio",
                territory_code="15001",
                eleccion="ayuntamiento",
                partido=partido,
                votos=votos,
            )
        )
    db.commit()


# ---------------------------------------------------------------------------
# service-level math test (calls service directly, no HTTP)
# ---------------------------------------------------------------------------

def test_derived_metrics_math():
    db = TestingSessionLocal()
    try:
        _seed(db)
        d = resultados_service.derived(db, None, 2021, "municipio", "15001", "ayuntamiento")
        # participación = (600+300+20)/1000 = 0.92 ; abstención = 0.08
        assert round(d["participacion"], 3) == 0.92
        assert round(d["abstencion"], 3) == 0.08
        # margen = (600-300) / 920 total_real (600+300)
        assert d["ganador"] == "MORENA"
        assert round(d["margen"], 3) == round((600 - 300) / 900, 3)
    finally:
        db.rollback()
        db.close()


# ---------------------------------------------------------------------------
# router tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_results():
    """Delete all ElectionResult rows before and after each test in this module."""
    db = TestingSessionLocal()
    db.query(ElectionResult).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(ElectionResult).delete()
    db.commit()
    db.close()


def _seed_global(db):
    """Seed global rows (organization_id=None)."""
    rows = [("MORENA", 600), ("PAN", 300), ("_NULOS", 20), ("_LISTA_NOMINAL", 1000)]
    for partido, votos in rows:
        db.add(
            ElectionResult(
                organization_id=None,
                anio=2021,
                nivel="municipio",
                territory_code="15001",
                eleccion="ayuntamiento",
                partido=partido,
                votos=votos,
            )
        )
    db.commit()


def test_resultados_endpoint_requires_auth(client):
    r = client.get("/api/resultados?anio=2021&nivel=municipio&eleccion=ayuntamiento")
    assert r.status_code == 401


def test_resultados_endpoint_returns_data(client):
    db = TestingSessionLocal()
    _seed_global(db)
    db.close()

    headers = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/resultados?anio=2021&nivel=municipio&eleccion=ayuntamiento", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert len(body["results"]) > 0, "Global rows must be visible to tenant user (global-OR-own scope)"


def test_resultados_derived_endpoint(client):
    db = TestingSessionLocal()
    _seed_global(db)
    db.close()

    headers = auth_headers(client, "admin@alpha.gov")
    r = client.get(
        "/api/resultados/derived?anio=2021&nivel=municipio&territory_code=15001&eleccion=ayuntamiento",
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ganador"] == "MORENA"
    assert round(body["participacion"], 3) == 0.92
