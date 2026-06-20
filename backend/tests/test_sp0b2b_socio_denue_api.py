"""Tests for socio_service + denue_service + /api/socio + /api/denue routers."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.economic_unit import EconomicUnit
from app.models.socio import SocioMetric
from app.services import denue_service, socio_service
from tests.conftest import TestingSessionLocal, auth_headers


# ---------------------------------------------------------------------------
# Autouse clean fixture — mirrors Task 7 pattern
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_tables():
    """Delete all rows from both tables before and after each test."""
    db = TestingSessionLocal()
    db.query(SocioMetric).delete()
    db.query(EconomicUnit).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(SocioMetric).delete()
    db.query(EconomicUnit).delete()
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Service-level tests (call services directly — no HTTP)
# ---------------------------------------------------------------------------


def test_socio_list():
    db = TestingSessionLocal()
    try:
        db.add(
            SocioMetric(
                organization_id=None,
                anio=2020,
                nivel="municipio",
                territory_code="15001",
                indicador="pobreza",
                valor=0.3,
            )
        )
        db.commit()
        out = socio_service.list_metrics(db, None, 2020, "municipio", "15001", None)
        assert len(out) == 1
        assert out[0]["indicador"] == "pobreza"
    finally:
        db.rollback()
        db.close()


def test_denue_geojson():
    db = TestingSessionLocal()
    try:
        import json

        db.add(
            EconomicUnit(
                organization_id=None,
                clave="D1",
                nombre="Tienda",
                territory_code="15001",
                lat=19.4,
                lon=-99.1,
                geometry=json.dumps({"lon": -99.1, "lat": 19.4}),
            )
        )
        db.commit()
        fc = denue_service.geojson(db, None, "15001", 100)
        assert fc["type"] == "FeatureCollection"
        assert fc["features"][0]["geometry"]["coordinates"] == [-99.1, 19.4]
    finally:
        db.rollback()
        db.close()


def test_denue_geojson_skips_null_latlon():
    """Rows with null lat/lon should not appear in the FeatureCollection."""
    db = TestingSessionLocal()
    try:
        db.add(
            EconomicUnit(
                organization_id=None,
                clave="D2",
                nombre="Sin Coords",
                territory_code="15001",
                lat=None,
                lon=None,
            )
        )
        db.commit()
        fc = denue_service.geojson(db, None, "15001", 100)
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 0
    finally:
        db.rollback()
        db.close()


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_socio_endpoint_requires_auth(client):
    r = client.get("/api/socio?anio=2020")
    assert r.status_code == 401


def test_denue_endpoint_requires_auth(client):
    r = client.get("/api/denue")
    assert r.status_code == 401


def test_denue_geojson_endpoint_requires_auth(client):
    r = client.get("/api/denue/geojson")
    assert r.status_code == 401


def test_socio_tenant_sees_global_rows(client):
    """Tenants must see global rows (organization_id IS NULL) — proves global-OR-own scope."""
    db = TestingSessionLocal()
    db.add(
        SocioMetric(
            organization_id=None,  # global row
            anio=2020,
            nivel="municipio",
            territory_code="15001",
            indicador="pobreza",
            valor=0.42,
        )
    )
    db.commit()
    db.close()

    headers = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/socio?anio=2020&territory_code=15001", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body
    assert len(body["metrics"]) > 0, "Global rows must be visible to tenant user (global-OR-own scope)"
    assert body["metrics"][0]["indicador"] == "pobreza"


def test_denue_tenant_sees_global_rows(client):
    """Tenants must see global DENUE rows (organization_id IS NULL)."""
    import json

    db = TestingSessionLocal()
    db.add(
        EconomicUnit(
            organization_id=None,  # global row
            clave="G1",
            nombre="Global Tienda",
            territory_code="15001",
            lat=19.4,
            lon=-99.1,
            geometry=json.dumps({"lon": -99.1, "lat": 19.4}),
        )
    )
    db.commit()
    db.close()

    headers = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/denue?territory_code=15001", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "units" in body
    assert len(body["units"]) > 0, "Global rows must be visible to tenant user (global-OR-own scope)"


def test_denue_geojson_endpoint_returns_feature_collection(client):
    """GeoJSON endpoint returns valid FeatureCollection for a tenant."""
    import json

    db = TestingSessionLocal()
    db.add(
        EconomicUnit(
            organization_id=None,
            clave="G2",
            nombre="Punto Global",
            territory_code="15002",
            lat=20.0,
            lon=-100.0,
            geometry=json.dumps({"lon": -100.0, "lat": 20.0}),
        )
    )
    db.commit()
    db.close()

    headers = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/denue/geojson?territory_code=15002", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1
    assert body["features"][0]["geometry"]["type"] == "Point"
    assert body["features"][0]["geometry"]["coordinates"] == [-100.0, 20.0]
