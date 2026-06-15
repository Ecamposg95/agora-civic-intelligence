"""Tests for the analytics overview — verifies real, tenant-scoped aggregates."""

from app.services.analytics_service import ACTIVITY_WINDOW_DAYS

from .conftest import auth_headers


def test_overview_requires_auth(client):
    assert client.get("/api/analytics/overview").status_code == 401


def test_overview_returns_real_tenant_scoped_metrics(client):
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/analytics/overview", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    summary = body["summary"]
    # Non-superadmin sees exactly their own organization.
    assert summary["organizations"] == 1
    # Alpha tenant seeded with 2 active users (admin + viewer).
    assert summary["users"] == 2
    # Data sources come from the INE source registry (non-empty).
    assert summary["data_sources"] >= 1
    assert summary["electoral_areas"] >= 0

    # Activity trend has one bucket per day in the window.
    activity = body["trends"]["activity"]
    assert len(activity) == ACTIVITY_WINDOW_DAYS
    assert all({"period", "value"} <= set(point) for point in activity)

    assert isinstance(body["coverage"], list)
    assert len(body["alerts"]) >= 1
    assert "generated_at" in body
