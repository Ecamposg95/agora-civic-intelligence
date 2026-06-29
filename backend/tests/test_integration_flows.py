"""End-to-end integration tests (SPA-4 Task 10, AC-9.1).

Each test exercises a complete HTTP flow through the TestClient — login, chain
of API calls, and assertion on the final state.  No service-layer mocks; every
assertion hits real endpoints that exercise real DB writes via the shared
SQLite pool.

Flows covered
-------------
1. Activist capture flow
2. Admin console flow
3. Compliance / ARCO flow
4. Export flow (masked + reveal)
5. RBAC / cross-tenant isolation
"""
from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy import select

from app.models.arco import ArcoRequest
from app.models.audit_log import AuditLog
from app.models.privacy import PrivacyAcceptance
from app.models.registro import Registro
from tests.conftest import (
    ALPHA_CAMPAIGN_ID,
    BETA_CAMPAIGN_ID,
    TestingSessionLocal,
    auth_headers,
)

# ---------------------------------------------------------------------------
# Helpers shared across flows
# ---------------------------------------------------------------------------


def _hdr(client, email, campaign_id=ALPHA_CAMPAIGN_ID):
    h = auth_headers(client, email)
    h["X-Campaign-Id"] = campaign_id
    return h


def _cleanup_registros_and_arco():
    """Hard-wipe all registros + related rows created during a flow test."""
    db = TestingSessionLocal()
    try:
        db.query(PrivacyAcceptance).delete()
        db.query(AuditLog).filter(
            AuditLog.action.in_([
                "registro.create",
                "registro.delete",
                "registro.reveal_clave",
                "registro.export",
                "registro.export.reveal",
                "registro.arco_hard_delete",
            ])
        ).delete()
        db.query(ArcoRequest).delete()
        db.query(Registro).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Flow 1: Activist capture — login → perfil → privacy notice → capture →
#          list (own) → clave masked; export blocked for activista.
# ---------------------------------------------------------------------------


class TestActivistCaptureFlow:
    """Full activist E2E path."""

    def test_flow(self, client):
        """
        1. Login as activista1.
        2. GET /perfil — lider_nombre present.
        3. GET /privacy/notice — v1 notice returned.
        4. POST /registros with consentimiento=True + clave.
        5. GET /registros/mios — registro appears, clave_masked only.
        6. GET /registros/{id} — same masking.
        7. activista cannot GET /registros/export.
        """
        try:
            h = _hdr(client, "activista1@alpha.gov")

            # 1+2. Login + perfil
            perfil = client.get("/api/perfil", headers=h)
            assert perfil.status_code == 200, perfil.text
            assert perfil.json()["lider_nombre"] == "Alpha Líder"
            assert "full_name" in perfil.json()
            assert perfil.json()["full_name"] == "Alpha Activista 1"

            # 3. Privacy notice must be published (v1 seeded in conftest)
            notice_resp = client.get("/api/privacy/notice", headers=h)
            assert notice_resp.status_code == 200, notice_resp.text
            notice_body = notice_resp.json()
            assert notice_body["version"] == "v1"
            assert notice_body["body"]  # non-empty

            # 4. Capture
            capture_resp = client.post(
                "/api/registros",
                json={
                    "nombre_completo": "Flow1 Activista",
                    "clave_elector": "ABCD1234567890XYZ8",
                    "seccion": "0001",
                    "consentimiento": True,
                },
                headers=h,
            )
            assert capture_resp.status_code == 201, capture_resp.text
            payload = capture_resp.json()
            rid = payload["id"]

            # Masking contract
            assert "clave_masked" in payload
            assert payload["clave_masked"].startswith("****-")
            assert "clave_elector" not in payload
            assert "clave_elector_enc" not in payload

            # 5. Own list
            list_resp = client.get("/api/registros/mios", headers=h)
            assert list_resp.status_code == 200, list_resp.text
            ids_in_list = [r["id"] for r in list_resp.json()["items"]]
            assert rid in ids_in_list
            for r in list_resp.json()["items"]:
                assert "clave_elector" not in r
                assert "clave_elector_enc" not in r

            # 6. Single-registro fetch (own)
            single_resp = client.get(f"/api/registros/{rid}", headers=h)
            assert single_resp.status_code == 200, single_resp.text
            assert "clave_elector" not in single_resp.json()
            assert single_resp.json()["clave_masked"].startswith("****-")

            # 7. Export blocked for activista
            export_resp = client.get(
                "/api/registros/export?format=csv", headers=h
            )
            assert export_resp.status_code == 403

        finally:
            _cleanup_registros_and_arco()


# ---------------------------------------------------------------------------
# Flow 2: Admin console — capture by activista → admin reads list, metricas,
#          reveals clave (audited) → audit endpoint shows the event.
# ---------------------------------------------------------------------------


class TestAdminConsoleFlow:
    """Full admin console E2E path."""

    def test_flow(self, client):
        """
        1. activista captures a registro.
        2. admin GET /admin/registros — sees it, masked, with organization_name.
        3. admin GET /admin/metricas — counts >= 1.
        4. admin POST /admin/registros/{id}/revelar-clave — plaintext returned.
        5. admin GET /admin/auditoria?action=registro.reveal_clave — event present.
        """
        try:
            act_h = _hdr(client, "activista1@alpha.gov")
            adm_h = _hdr(client, "admin@alpha.gov")

            # 1. Capture
            cap = client.post(
                "/api/registros",
                json={
                    "nombre_completo": "Flow2 Admin Test",
                    "clave_elector": "ABCD1234567890XYZ8",
                    "consentimiento": True,
                },
                headers=act_h,
            )
            assert cap.status_code == 201, cap.text
            rid = cap.json()["id"]

            # 2. Admin list
            list_resp = client.get("/api/admin/registros", headers=adm_h)
            assert list_resp.status_code == 200, list_resp.text
            list_body = list_resp.json()
            assert list_body["total"] >= 1
            items = list_body["items"]
            assert "organization_name" in items[0]
            # Clave never leaks in listing
            for item in items:
                assert "clave_elector" not in item
                assert "clave_elector_enc" not in item

            # 3. Metricas
            met = client.get("/api/admin/metricas", headers=adm_h)
            assert met.status_code == 200, met.text
            assert met.json()["total"] >= 1

            # 4. Reveal clave
            reveal = client.post(
                f"/api/admin/registros/{rid}/revelar-clave", headers=adm_h
            )
            assert reveal.status_code == 200, reveal.text
            assert reveal.json()["clave_elector"] == "ABCD1234567890XYZ8"

            # 5. Audit shows the reveal event
            aud = client.get(
                "/api/admin/auditoria?action=registro.reveal_clave",
                headers=adm_h,
            )
            assert aud.status_code == 200, aud.text
            assert aud.json()["total"] >= 1

        finally:
            _cleanup_registros_and_arco()


# ---------------------------------------------------------------------------
# Flow 3: Compliance / ARCO — capture → privacy acceptance trail →
#          ARCO solicitud → ejecutar (hard-delete) → row GONE, audit persists.
# ---------------------------------------------------------------------------


class TestComplianceArcoFlow:
    """Privacy consent + ARCO hard-delete E2E path."""

    def test_flow(self, client, seed_data):
        """
        1. Activista captures — notice v1 linked, PrivacyAcceptance written.
        2. Admin creates ARCO solicitud (CANCELACION).
        3. Admin ejecuta the solicitud → deleted=1.
        4. Registro is physically gone from DB.
        5. ArcoRequest trail row persists (PROCESADA).
        6. AuditLog entry with action=registro.arco_hard_delete persists.
        """
        try:
            act_h = _hdr(client, "activista1@alpha.gov")
            adm_h = _hdr(client, "admin@alpha.gov")

            # 1. Capture
            cap = client.post(
                "/api/registros",
                json={
                    "nombre_completo": "Flow3 ARCO Subject",
                    "consentimiento": True,
                },
                headers=act_h,
            )
            assert cap.status_code == 201, cap.text
            rid = cap.json()["id"]

            # Privacy acceptance trail must exist
            db = TestingSessionLocal()
            try:
                acc = db.execute(
                    select(PrivacyAcceptance).where(
                        PrivacyAcceptance.registro_id == rid
                    )
                ).scalar_one_or_none()
                assert acc is not None, "PrivacyAcceptance must be created on capture"
                assert acc.aviso_version == "v1"
            finally:
                db.close()

            # 2. Admin creates ARCO solicitud
            sol = client.post(
                "/api/arco/solicitudes",
                json={
                    "registro_id": rid,
                    "tipo": "CANCELACION",
                    "motivo": "Derecho de cancelación",
                    "titular_ref": "MASKED",
                },
                headers=adm_h,
            )
            assert sol.status_code == 201, sol.text
            sol_id = sol.json()["id"]

            # 3. Execute hard-delete
            ej = client.post(
                f"/api/arco/solicitudes/{sol_id}/ejecutar", headers=adm_h
            )
            assert ej.status_code == 200, ej.text
            assert ej.json()["deleted"] == 1

            # 4. Registro GONE from DB
            db2 = TestingSessionLocal()
            try:
                row = db2.execute(
                    select(Registro).where(Registro.id == rid)
                ).scalar_one_or_none()
                assert row is None, "Registro must be physically deleted after ARCO ejecutar"

                # Privacy acceptance cascaded away
                acc_after = db2.execute(
                    select(PrivacyAcceptance).where(
                        PrivacyAcceptance.registro_id == rid
                    )
                ).scalar_one_or_none()
                assert acc_after is None, "PrivacyAcceptance must cascade-delete with Registro"

                # 5. ArcoRequest trail persists
                arco_row = db2.execute(
                    select(ArcoRequest).where(ArcoRequest.id == sol_id)
                ).scalar_one_or_none()
                assert arco_row is not None, "ArcoRequest trail must persist"
                from app.models.arco import ArcoEstado
                assert arco_row.estado == ArcoEstado.PROCESADA

                # 6. AuditLog persists
                audit_row = db2.execute(
                    select(AuditLog).where(
                        AuditLog.entity_id == rid,
                        AuditLog.action == "registro.arco_hard_delete",
                    )
                ).scalar_one_or_none()
                assert audit_row is not None, "AuditLog must be written for ARCO hard-delete"

            finally:
                db2.close()

        finally:
            _cleanup_registros_and_arco()


# ---------------------------------------------------------------------------
# Flow 4: Export — admin exports CSV (masked) then reveal=true (plaintext +
#         audit); LIDER sees only their estructura; cross-tenant isolation.
# ---------------------------------------------------------------------------


class TestExportFlow:
    """Export CSV masked + reveal E2E path."""

    def test_masked_export_then_reveal_export(self, client):
        """
        1. Activista captures with clave.
        2. Admin exports CSV (no reveal) — clave is masked.
        3. Admin exports CSV (reveal=true) — plaintext clave, audit written.
        """
        try:
            act_h = _hdr(client, "activista1@alpha.gov")
            adm_h = _hdr(client, "admin@alpha.gov")

            # 1. Capture
            cap = client.post(
                "/api/registros",
                json={
                    "nombre_completo": "Flow4 Export",
                    "clave_elector": "ABCD1234567890XYZ8",
                    "consentimiento": True,
                },
                headers=act_h,
            )
            assert cap.status_code == 201, cap.text

            # 2. Masked export
            resp_masked = client.get(
                "/api/registros/export?format=csv", headers=adm_h
            )
            assert resp_masked.status_code == 200, resp_masked.text
            assert "text/csv" in resp_masked.headers["content-type"]
            rows = list(csv.DictReader(io.StringIO(resp_masked.text)))
            assert len(rows) >= 1
            clave_col = rows[0].get("clave", "")
            assert clave_col.startswith("****-"), f"Expected masked, got: {clave_col}"
            assert "ABCD1234567890XYZ8" not in resp_masked.text

            # 3. Reveal export — plaintext + audit
            resp_reveal = client.get(
                "/api/registros/export?format=csv&reveal=true", headers=adm_h
            )
            assert resp_reveal.status_code == 200, resp_reveal.text
            rows_reveal = list(csv.DictReader(io.StringIO(resp_reveal.text)))
            assert rows_reveal[0]["clave"] == "ABCD1234567890XYZ8"

            db = TestingSessionLocal()
            try:
                reveal_audits = db.execute(
                    select(AuditLog).where(AuditLog.action == "registro.export.reveal")
                ).scalars().all()
                assert len(reveal_audits) >= 1, "registro.export.reveal audit must be written"
                # No PII in meta
                for a in reveal_audits:
                    assert "ABCD1234567890XYZ8" not in str(a.meta or "")
            finally:
                db.close()

        finally:
            _cleanup_registros_and_arco()

    def test_lider_export_scope(self, client):
        """Lider export only sees their activistas' registros, not beta tenant."""
        try:
            lider_h = _hdr(client, "lider@alpha.gov")
            act1_h = _hdr(client, "activista1@alpha.gov")
            beta_h = _hdr(client, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)

            # Capture from alpha activista1 (under lider) and beta
            r1 = client.post(
                "/api/registros",
                json={"nombre_completo": "Flow4 Lider Scope", "consentimiento": True},
                headers=act1_h,
            )
            assert r1.status_code == 201, r1.text

            r2 = client.post(
                "/api/registros",
                json={"nombre_completo": "Flow4 Beta Invisible", "consentimiento": True},
                headers=beta_h,
            )
            assert r2.status_code == 201, r2.text

            lider_export = client.get(
                "/api/registros/export?format=csv", headers=lider_h
            )
            assert lider_export.status_code == 200, lider_export.text
            nombres = [row["nombre_completo"] for row in csv.DictReader(io.StringIO(lider_export.text))]
            assert "Flow4 Lider Scope" in nombres
            assert "Flow4 Beta Invisible" not in nombres

        finally:
            _cleanup_registros_and_arco()


# ---------------------------------------------------------------------------
# Flow 5: RBAC / isolation
# ---------------------------------------------------------------------------


class TestRbacIsolationFlow:
    """RBAC gate checks and cross-tenant isolation wired end-to-end."""

    def test_activista_cannot_see_other_activista_registro(self, client):
        """activista1's registro is invisible to activista2 (404 not 403)."""
        try:
            h1 = _hdr(client, "activista1@alpha.gov")
            h2 = _hdr(client, "activista2@alpha.gov")

            cap = client.post(
                "/api/registros",
                json={"nombre_completo": "Flow5 Private A1", "consentimiento": True},
                headers=h1,
            )
            assert cap.status_code == 201, cap.text
            rid = cap.json()["id"]

            # activista2 must NOT see it
            assert client.get(f"/api/registros/{rid}", headers=h2).status_code == 404

            # activista2's own list must NOT contain it
            lst = client.get("/api/registros/mios", headers=h2)
            assert lst.status_code == 200
            ids = [r["id"] for r in lst.json()["items"]]
            assert rid not in ids

        finally:
            _cleanup_registros_and_arco()

    def test_viewer_blocked_on_all_write_and_admin_endpoints(self, client):
        """Viewer role blocked from registros write and all admin endpoints."""
        v_h = _hdr(client, "viewer@alpha.gov")

        assert client.post(
            "/api/registros",
            json={"nombre_completo": "Blocked", "consentimiento": True},
            headers=v_h,
        ).status_code == 403

        assert client.get("/api/registros/mios", headers=v_h).status_code == 403
        assert client.get("/api/admin/registros", headers=v_h).status_code == 403
        assert client.get("/api/admin/metricas", headers=v_h).status_code == 403
        assert client.get("/api/admin/estructura", headers=v_h).status_code == 403

    def test_cross_tenant_isolation_admin_cannot_see_other_org(self, client):
        """Alpha admin cannot list Beta's registros."""
        try:
            beta_h = _hdr(client, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
            adm_alpha_h = _hdr(client, "admin@alpha.gov")

            cap = client.post(
                "/api/registros",
                json={"nombre_completo": "Flow5 Beta Record", "consentimiento": True},
                headers=beta_h,
            )
            assert cap.status_code == 201, cap.text
            beta_rid = cap.json()["id"]

            # Alpha admin listing must NOT include beta's registro
            alpha_list = client.get("/api/admin/registros", headers=adm_alpha_h)
            assert alpha_list.status_code == 200
            alpha_ids = [r["id"] for r in alpha_list.json()["items"]]
            assert beta_rid not in alpha_ids

        finally:
            _cleanup_registros_and_arco()

    def test_superadmin_consolidated_sees_all_tenants(self, client):
        """Superadmin without X-Campaign-Id sees registros from any tenant."""
        try:
            act_h = _hdr(client, "activista1@alpha.gov")
            beta_h = _hdr(client, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
            super_h = auth_headers(client, "super@atlas.gov")

            cap_alpha = client.post(
                "/api/registros",
                json={"nombre_completo": "Flow5 Super Alpha", "consentimiento": True},
                headers=act_h,
            )
            assert cap_alpha.status_code == 201, cap_alpha.text

            cap_beta = client.post(
                "/api/registros",
                json={"nombre_completo": "Flow5 Super Beta", "consentimiento": True},
                headers=beta_h,
            )
            assert cap_beta.status_code == 201, cap_beta.text

            # Superadmin consolidated (no campaign header)
            consolidated = client.get("/api/admin/registros", headers=super_h)
            assert consolidated.status_code == 200, consolidated.text
            nombres = {r["nombre_completo"] for r in consolidated.json()["items"]}
            assert "Flow5 Super Alpha" in nombres
            assert "Flow5 Super Beta" in nombres

        finally:
            _cleanup_registros_and_arco()

    def test_lider_forbidden_on_reveal_clave(self, client):
        """Lider (not admin) cannot reveal a clave — must get 403."""
        try:
            act_h = _hdr(client, "activista1@alpha.gov")
            lider_h = _hdr(client, "lider@alpha.gov")

            cap = client.post(
                "/api/registros",
                json={
                    "nombre_completo": "Flow5 Lider Reveal",
                    "clave_elector": "ABCD1234567890XYZ8",
                    "consentimiento": True,
                },
                headers=act_h,
            )
            assert cap.status_code == 201, cap.text
            rid = cap.json()["id"]

            resp = client.post(
                f"/api/admin/registros/{rid}/revelar-clave", headers=lider_h
            )
            assert resp.status_code == 403

        finally:
            _cleanup_registros_and_arco()

    def test_arco_cross_tenant_blocked(self, client):
        """Beta admin cannot execute an ARCO solicitud that belongs to Alpha."""
        try:
            act_h = _hdr(client, "activista1@alpha.gov")
            adm_alpha_h = _hdr(client, "admin@alpha.gov")
            adm_beta_h = _hdr(client, "admin@beta.gov", BETA_CAMPAIGN_ID)

            # Alpha activista captures
            cap = client.post(
                "/api/registros",
                json={"nombre_completo": "Flow5 ARCO Cross", "consentimiento": True},
                headers=act_h,
            )
            assert cap.status_code == 201, cap.text
            rid = cap.json()["id"]

            # Alpha admin creates solicitud
            sol = client.post(
                "/api/arco/solicitudes",
                json={
                    "registro_id": rid,
                    "tipo": "CANCELACION",
                    "motivo": "Cross-tenant test",
                    "titular_ref": "MASKED",
                },
                headers=adm_alpha_h,
            )
            assert sol.status_code == 201, sol.text
            sol_id = sol.json()["id"]

            # Beta admin tries to execute — must get 404
            ej = client.post(
                f"/api/arco/solicitudes/{sol_id}/ejecutar", headers=adm_beta_h
            )
            assert ej.status_code == 404, (
                f"Beta admin must not execute Alpha solicitud; got {ej.status_code}: {ej.text}"
            )

        finally:
            _cleanup_registros_and_arco()
