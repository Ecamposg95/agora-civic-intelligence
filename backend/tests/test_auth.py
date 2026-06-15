"""Authentication flow tests."""

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, auth_headers


def test_login_success(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/login", json={"email": "admin@alpha.gov", "password": PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_login_invalid_credentials(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/login", json={"email": "admin@alpha.gov", "password": "wrong"}
    )
    assert resp.status_code == 401
    # Standard error envelope (Golden Rule #8).
    assert resp.json()["error"]["status"] == 401


def test_login_validation_error_envelope(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 422
    assert "error" in resp.json()


def test_me_returns_current_user(client: TestClient) -> None:
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "admin@alpha.gov"
    assert body["role"] == "admin"
    assert isinstance(body["id"], str)


def test_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
