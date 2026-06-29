"""Tests for admin_service.metrics — scope, counts, daily buckets."""
from app.models.registro import Registro
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID, BETA_CAMPAIGN_ID


def test_metricas_totals_and_daily():
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx, _make
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P1", seccion="0001")
        _make(db, a1, "P2", seccion="0001")
        m = admin_service.metrics(db, admin)
        assert m["total"] == 2
        # by_activista: a bucket with count 2 for activista1
        assert any(b["count"] == 2 for b in m["by_activista"])
        # by_seccion: a bucket for "0001" with count 2
        assert any(b["label"] == "0001" and b["count"] == 2 for b in m["by_seccion"])
        # by_lider: a bucket for Alpha Líder with count 2 (activista1 belongs to them)
        assert any(b["label"] == "Alpha Líder" and b["count"] == 2 for b in m["by_lider"])
        # avance_diario / by_day: sum matches total
        assert sum(p["count"] for p in m["by_day"]) == 2
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_metricas_admin_scope_only_own_campaign():
    """Admin only sees registros in their campaign (tenant isolation)."""
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx, _make
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        ab = _camp_ctx(db, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "Alpha P")
        _make(db, ab, "Beta P")
        m = admin_service.metrics(db, admin)
        # Admin of alpha only sees 1 registro (their campaign)
        assert m["total"] == 1
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_metricas_lider_scope_only_own_estructura():
    """Lider metrics only count registros from their activistas."""
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx, _make
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        lider = _camp_ctx(db, "lider@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P1")
        _make(db, a1, "P2")
        m = admin_service.metrics(db, lider)
        # Lider sees both (activista1 is under this lider)
        assert m["total"] == 2
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_metricas_superadmin_consolidated():
    """Superadmin with no org_id sees all registros across tenants."""
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx, _consolidated_ctx, _make
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        ab = _camp_ctx(db, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
        _make(db, a1, "Alpha P")
        _make(db, ab, "Beta P")
        m = admin_service.metrics(db, _consolidated_ctx(db))
        assert m["total"] == 2
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
