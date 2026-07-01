"""TDD tests for two default-deny RBAC gaps found in the platform review:

1. `GET /ingest/datasets|runs|runs/{id}` were open to any authenticated org user
   (only `Tenant`), letting VIEWER/CONSULTA/ACTIVISTA enumerate ingest provenance.
   They should be gated to the data-governance roles (ADMIN + ANALYST), matching
   the sibling `sources` router.
2. `POST /campaigns/{id}/contests` (a structural write) was open to any campaign
   member regardless of role, while `POST /campaigns` requires ADMIN. Creating a
   contest is an admin-level write and must be ADMIN-gated.

RED: run before the guards are added to confirm the current (insecure) behavior.
GREEN: run after gating to confirm the holes are closed.
"""
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID


def _ch(client, email):
    """Auth headers WITH the Alpha campaign context."""
    return {**auth_headers(client, email), "X-Campaign-Id": ALPHA_CAMPAIGN_ID}


# ---------------------------------------------------------------------------
# Gap 1 — ingest read endpoints must be gated to ADMIN + ANALYST
# ---------------------------------------------------------------------------

_INGEST_READS = ["/api/ingest/datasets", "/api/ingest/runs"]

_BLOCKED_ON_INGEST = [
    "viewer@alpha.gov",      # VIEWER
    "consulta@alpha.gov",    # CONSULTA
    "activista1@alpha.gov",  # ACTIVISTA
    "capturista@alpha.gov",  # CAPTURISTA
    "coord@alpha.gov",       # COORDINADOR
    "lider@alpha.gov",       # LIDER
]


def test_ingest_reads_blocked_for_non_governance_roles(client):
    for email in _BLOCKED_ON_INGEST:
        for path in _INGEST_READS:
            r = client.get(path, headers=auth_headers(client, email))
            assert r.status_code == 403, f"{email} {path} -> {r.status_code} (expected 403)"


def test_ingest_reads_allowed_for_admin_and_analyst(client):
    for email in ("admin@alpha.gov", "analyst@alpha.gov"):
        for path in _INGEST_READS:
            r = client.get(path, headers=auth_headers(client, email))
            assert r.status_code == 200, f"{email} {path} -> {r.status_code} (expected 200)"


# ---------------------------------------------------------------------------
# Gap 2 — POST /campaigns/{id}/contests must be ADMIN-gated
# ---------------------------------------------------------------------------

def _first_cargo_id(client):
    r = client.get("/api/catalogs/cargos", headers=auth_headers(client, "admin@alpha.gov"))
    assert r.status_code == 200, r.text
    cargos = r.json()
    assert cargos, "expected at least one seeded cargo"
    return cargos[0]["id"]


def test_non_admin_member_cannot_create_contest(client):
    cargo_id = _first_cargo_id(client)
    # viewer@alpha.gov IS a member of the Alpha campaign but is not ADMIN.
    r = client.post(
        f"/api/campaigns/{ALPHA_CAMPAIGN_ID}/contests",
        json={"cargo_id": cargo_id},
        headers=_ch(client, "viewer@alpha.gov"),
    )
    assert r.status_code == 403, r.text


def test_admin_can_create_contest(client):
    cargo_id = _first_cargo_id(client)
    r = client.post(
        f"/api/campaigns/{ALPHA_CAMPAIGN_ID}/contests",
        json={"cargo_id": cargo_id},
        headers=_ch(client, "admin@alpha.gov"),
    )
    assert r.status_code == 201, r.text
