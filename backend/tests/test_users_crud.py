"""Advanced users CRUD: RBAC, lifecycle, forced password change, isolation."""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _org_id(client: TestClient, email: str) -> str:
    return client.get("/api/auth/me", headers=auth_headers(client, email)).json()[
        "organization_id"
    ]


def test_admin_creates_user_with_temp_password(client: TestClient) -> None:
    h = auth_headers(client, "admin@alpha.gov")
    resp = client.post(
        "/api/users",
        headers=h,
        json={"email": "nuevo@alpha.gov", "full_name": "Nuevo", "role": "analyst"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["temporary_password"]
    assert body["user"]["must_change_password"] is True
    assert body["user"]["organization_id"] == _org_id(client, "admin@alpha.gov")
    assert body["user"]["role"] == "analyst"


def test_viewer_cannot_create_user(client: TestClient) -> None:
    h = auth_headers(client, "viewer@alpha.gov")
    resp = client.post(
        "/api/users",
        headers=h,
        json={"email": "x@alpha.gov", "full_name": "X", "role": "viewer"},
    )
    assert resp.status_code == 403


def test_admin_cannot_grant_superadmin(client: TestClient) -> None:
    h = auth_headers(client, "admin@alpha.gov")
    resp = client.post(
        "/api/users",
        headers=h,
        json={"email": "sa@alpha.gov", "full_name": "SA", "role": "superadmin"},
    )
    assert resp.status_code == 403


def test_duplicate_email_conflict(client: TestClient) -> None:
    h = auth_headers(client, "admin@alpha.gov")
    resp = client.post(
        "/api/users",
        headers=h,
        json={"email": "admin@alpha.gov", "full_name": "Dup", "role": "viewer"},
    )
    assert resp.status_code == 409


def test_forced_password_change_flow(client: TestClient) -> None:
    admin = auth_headers(client, "admin@alpha.gov")
    email = "forced@alpha.gov"
    created = client.post(
        "/api/users",
        headers=admin,
        json={"email": email, "full_name": "Forced", "role": "viewer"},
    ).json()
    temp = created["temporary_password"]

    token = client.post(
        "/api/auth/login", json={"email": email, "password": temp}
    ).json()["access_token"]
    nh = {"Authorization": f"Bearer {token}"}

    # Tenant features are blocked until the password is changed.
    blocked = client.get("/api/analytics/overview", headers=nh)
    assert blocked.status_code == 428

    changed = client.post(
        "/api/users/me/change-password",
        headers=nh,
        json={"current_password": temp, "new_password": "BrandNew123"},
    )
    assert changed.status_code == 204

    # Now tenant features are reachable.
    assert client.get("/api/analytics/overview", headers=nh).status_code == 200


def test_user_lifecycle(client: TestClient) -> None:
    admin = auth_headers(client, "admin@alpha.gov")
    uid = client.post(
        "/api/users",
        headers=admin,
        json={"email": "life@alpha.gov", "full_name": "Life", "role": "analyst"},
    ).json()["user"]["id"]

    updated = client.patch(
        f"/api/users/{uid}",
        headers=admin,
        json={"full_name": "Life Updated", "phone": "+52 555 111"},
    ).json()
    assert updated["full_name"] == "Life Updated"
    assert updated["phone"] == "+52 555 111"

    assert client.post(f"/api/users/{uid}/deactivate", headers=admin).json()["is_active"] is False
    assert client.post(f"/api/users/{uid}/activate", headers=admin).json()["is_active"] is True

    assert client.delete(f"/api/users/{uid}", headers=admin).status_code == 204
    ids = [u["id"] for u in client.get("/api/users", headers=admin).json()["items"]]
    assert uid not in ids
    ids_all = [
        u["id"]
        for u in client.get("/api/users?include_deleted=true", headers=admin).json()["items"]
    ]
    assert uid in ids_all

    restored = client.post(f"/api/users/{uid}/restore", headers=admin)
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


def test_admin_reset_password(client: TestClient) -> None:
    admin = auth_headers(client, "admin@alpha.gov")
    uid = client.post(
        "/api/users",
        headers=admin,
        json={"email": "reset@alpha.gov", "full_name": "Reset", "role": "viewer"},
    ).json()["user"]["id"]
    resp = client.post(f"/api/users/{uid}/reset-password", headers=admin)
    assert resp.status_code == 200
    assert resp.json()["temporary_password"]
    assert resp.json()["user_id"] == uid


def test_cross_tenant_get_is_404(client: TestClient) -> None:
    alpha = auth_headers(client, "admin@alpha.gov")
    beta_me = client.get("/api/auth/me", headers=auth_headers(client, "admin@beta.gov")).json()
    resp = client.get(f"/api/users/{beta_me['id']}", headers=alpha)
    assert resp.status_code == 404


def test_admin_cannot_delete_self(client: TestClient) -> None:
    admin = auth_headers(client, "admin@alpha.gov")
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.delete(f"/api/users/{me['id']}", headers=admin).status_code == 403


def test_search_and_filter(client: TestClient) -> None:
    admin = auth_headers(client, "admin@alpha.gov")
    by_role = client.get("/api/users?role=viewer", headers=admin).json()
    assert all(u["role"] == "viewer" for u in by_role["items"])
    search = client.get("/api/users?q=admin@alpha", headers=admin).json()
    assert any(u["email"] == "admin@alpha.gov" for u in search["items"])
