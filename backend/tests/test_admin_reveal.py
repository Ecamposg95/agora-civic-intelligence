"""TDD tests for admin_service.reveal_clave — audited Fernet decrypt."""
import pytest
from app.models.registro import Registro
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID, BETA_CAMPAIGN_ID
from tests.test_admin_registros import _camp_ctx, _make


def test_reveal_decrypts_and_audits():
    from app.services import admin_service
    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        reg = _make(db, a1, "Con Clave", clave_elector="ABCD1234567890XYZ8")
        plain = admin_service.reveal_clave(db, admin, reg.id)
        assert plain == "ABCD1234567890XYZ8"
        audit = db.execute(
            select(AuditLog).where(
                AuditLog.action == "registro.reveal_clave",
                AuditLog.entity_id == reg.id,
            )
        ).scalars().all()
        assert len(audit) == 1
        assert audit[0].organization_id == reg.organization_id
    finally:
        db.query(Registro).delete()
        db.commit()
        db.close()


def test_reveal_no_clave_raises():
    from app.services import admin_service

    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        reg = _make(db, a1, "Sin Clave")
        with pytest.raises(admin_service.NoClave):
            admin_service.reveal_clave(db, admin, reg.id)
    finally:
        db.query(Registro).delete()
        db.commit()
        db.close()


def test_reveal_out_of_scope_returns_none():
    """A registro from org BETA is invisible to an ALPHA admin — reveal returns None."""
    from app.services import admin_service

    db = TestingSessionLocal()
    try:
        ab = _camp_ctx(db, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
        alpha_admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        beta_reg = _make(db, ab, "Beta Person", clave_elector="BETA1234567890XYZ8")
        result = admin_service.reveal_clave(db, alpha_admin, beta_reg.id)
        assert result is None
    finally:
        db.query(Registro).delete()
        db.commit()
        db.close()
