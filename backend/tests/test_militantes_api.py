"""API tests for /api/militantes (router wiring, RBAC, route ordering).

Note: the task brief assumed fixtures named `activista_client` / `campaign_headers`.
Neither exists in this repo's conftest.py. The established pattern (see
tests/test_registro_captura_v2.py) is the session-scoped `client` TestClient
fixture + the `auth_headers(client, email)` helper, with X-Campaign-Id attached
manually. activista1@alpha.gov already has a CampaignMembership in
ALPHA_CAMPAIGN_ID (seeded in conftest.py's seed_data fixture), so no new
membership fixture is required.
"""
from tests.conftest import ALPHA_CAMPAIGN_ID, auth_headers


def _hdr(client, email, campaign_id=ALPHA_CAMPAIGN_ID):
    h = auth_headers(client, email)
    h["X-Campaign-Id"] = campaign_id
    return h


def test_create_and_list_militante(client):
    h = _hdr(client, "activista1@alpha.gov")
    r = client.post("/api/militantes", headers=h, json={
        "nombre_completo": "API Test", "consentimiento": True, "seccion": "4127"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["folio"].startswith("SMA-")
    lst = client.get("/api/militantes", headers=h)
    assert lst.status_code == 200
    assert lst.json()["total"] >= 1


def test_activista_cannot_reveal(client):
    h = _hdr(client, "activista1@alpha.gov")
    r = client.post("/api/militantes", headers=h, json={
        "nombre_completo": "Rev Test", "consentimiento": True, "seccion": "4127"})
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    rev = client.get(f"/api/militantes/reveal/{mid}", headers=h)
    assert rev.status_code == 403


def test_activista_cannot_access_panorama(client):
    h = _hdr(client, "activista1@alpha.gov")
    r = client.get("/api/militantes/panorama", headers=h)
    assert r.status_code == 403


def test_coordinador_can_reveal_and_panorama(client):
    ha = _hdr(client, "activista1@alpha.gov")
    r = client.post("/api/militantes", headers=ha, json={
        "nombre_completo": "Coord Reveal", "consentimiento": True,
        "curp": "CURP010101HDFRRL09", "seccion": "4127"})
    mid = r.json()["id"]

    hc = _hdr(client, "coord@alpha.gov")
    rev = client.get(f"/api/militantes/reveal/{mid}", headers=hc)
    assert rev.status_code == 200, rev.text
    assert rev.json()["curp"] == "CURP010101HDFRRL09"

    pan = client.get("/api/militantes/panorama", headers=hc)
    assert pan.status_code == 200, pan.text
    assert "kpis" in pan.json()


def test_militante_read_never_exposes_curp_or_clave(client):
    h = _hdr(client, "activista1@alpha.gov")
    r = client.post("/api/militantes", headers=h, json={
        "nombre_completo": "No Leak", "consentimiento": True,
        "curp": "CURP010101HDFRRL09", "clave_elector": "ABCD1234567890XYZ8",
        "seccion": "4127"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert "curp" not in body
    assert "clave_elector" not in body
    assert body["curp_masked"]
    assert body["clave_masked"] == "****-XYZ8"


def test_create_without_consent_returns_422(client):
    h = _hdr(client, "activista1@alpha.gov")
    r = client.post("/api/militantes", headers=h, json={
        "nombre_completo": "Sin Consentimiento", "consentimiento": False})
    assert r.status_code == 422, r.text


def test_panorama_route_not_captured_by_mid_route(client):
    """`/militantes/panorama` must resolve to the panorama endpoint, not get_one(mid)."""
    hc = _hdr(client, "coord@alpha.gov")
    r = client.get("/api/militantes/panorama", headers=hc)
    assert r.status_code == 200
    assert "kpis" in r.json()  # not a 404 "Militante no encontrado"


def test_estado_update_requires_review_role(client):
    ha = _hdr(client, "activista1@alpha.gov")
    r = client.post("/api/militantes", headers=ha, json={
        "nombre_completo": "Estado Test", "consentimiento": True, "seccion": "4127"})
    mid = r.json()["id"]

    forbidden = client.patch(f"/api/militantes/{mid}/estado", headers=ha,
                              json={"estado": "VALIDADO"})
    assert forbidden.status_code == 403

    hc = _hdr(client, "coord@alpha.gov")
    ok = client.patch(f"/api/militantes/{mid}/estado", headers=hc,
                       json={"estado": "VALIDADO"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["estado"] == "VALIDADO"


def test_activista_can_delete_own_militante(client):
    """Soft-delete removes the militante from scoped views (list/panorama)."""
    h = _hdr(client, "activista1@alpha.gov")
    r = client.post("/api/militantes", headers=h, json={
        "nombre_completo": "Del Test", "consentimiento": True, "seccion": "4127"})
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    d = client.delete(f"/api/militantes/{mid}", headers=h)
    assert d.status_code == 204, d.text
    # gone from scoped get + list
    assert client.get(f"/api/militantes/{mid}", headers=h).status_code == 404
    ids = [m["id"] for m in client.get("/api/militantes", headers=h).json()["items"]]
    assert mid not in ids
    # second delete is a 404 (already gone)
    assert client.delete(f"/api/militantes/{mid}", headers=h).status_code == 404
