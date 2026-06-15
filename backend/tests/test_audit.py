"""Tests for the read-only audit endpoint."""

from .conftest import auth_headers


def _seed_login_events(client):
    # Each successful login writes an audit entry (auth flow records it).
    auth_headers(client, "admin@alpha.gov")
    auth_headers(client, "admin@alpha.gov")


def test_audit_requires_auth(client):
    assert client.get("/api/audit").status_code == 401


def test_viewer_forbidden(client):
    headers = auth_headers(client, "viewer@alpha.gov")
    assert client.get("/api/audit", headers=headers).status_code == 403


def test_admin_sees_paginated_tenant_events(client):
    _seed_login_events(client)
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/audit?limit=5", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) >= {"items", "total", "limit", "offset"}
    assert body["limit"] == 5
    assert body["total"] >= 1
    for item in body["items"]:
        assert {"id", "action", "created_at"} <= set(item)


def test_action_filter(client):
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/audit?action=auth.login", headers=headers)
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        assert item["action"] == "auth.login"


def test_admin_does_not_see_other_tenant_events(client):
    # Logging in writes an auth.login audit row scoped to each user's org.
    alpha_headers = auth_headers(client, "admin@alpha.gov")
    beta_headers = auth_headers(client, "admin@beta.gov")

    alpha_resp = client.get("/api/audit", headers=alpha_headers)
    beta_resp = client.get("/api/audit", headers=beta_headers)
    assert alpha_resp.status_code == 200, alpha_resp.text
    assert beta_resp.status_code == 200, beta_resp.text

    alpha_orgs = {item["organization_id"] for item in alpha_resp.json()["items"]}
    beta_orgs = {item["organization_id"] for item in beta_resp.json()["items"]}

    # Each tenant sees its own events and exactly one org id, and they never overlap.
    assert alpha_orgs and beta_orgs
    assert len(alpha_orgs) == 1 and len(beta_orgs) == 1
    assert alpha_orgs.isdisjoint(beta_orgs)
