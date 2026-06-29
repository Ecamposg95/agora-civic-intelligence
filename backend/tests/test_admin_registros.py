"""Service-level tests for admin listing with filters + base column."""
from app.models.registro import Registro
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID, BETA_CAMPAIGN_ID


def _camp_ctx(db, email, campaign_id):
    from sqlalchemy import select
    from app.dependencies import CampaignContext
    from app.models.user import User
    from app.models.campaign import Campaign
    user = db.execute(select(User).where(User.email == email)).scalar_one()
    camp = db.execute(select(Campaign).where(Campaign.id == campaign_id)).scalar_one()
    org = camp.organization_id if user.role.value == "superadmin" else user.organization_id
    return CampaignContext(user=user, organization_id=org, role=user.role, campaign_id=campaign_id)


def _consolidated_ctx(db):
    from sqlalchemy import select
    from app.dependencies import CampaignContext
    from app.models.user import User
    su = db.execute(select(User).where(User.email == "super@atlas.gov")).scalar_one()
    return CampaignContext(user=su, organization_id=None, role=su.role, campaign_id="")


def _make(db, ctx, nombre, **kw):
    from app.services import registro_service
    from app.schemas.registro import RegistroCreate
    return registro_service.create_registro(db, ctx, RegistroCreate(nombre_completo=nombre, consentimiento=True, **kw))


def test_admin_sees_full_campaign_with_base():
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        a2 = _camp_ctx(db, "activista2@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P A1", seccion="0001")
        _make(db, a2, "P A2", seccion="0002")
        rows, total = admin_service.list_admin_registros(db, admin, q=None, lider_id=None,
            activista_id=None, seccion=None, since=None, until=None, limit=50, offset=0)
        assert total == 2
        assert all(r["organization_name"] for r in rows)  # base column present
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_superadmin_consolidated_sees_multiple_orgs():
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        ab = _camp_ctx(db, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
        _make(db, a1, "Alpha P")
        _make(db, ab, "Beta P")
        rows, total = admin_service.list_admin_registros(db, _consolidated_ctx(db), q=None, lider_id=None,
            activista_id=None, seccion=None, since=None, until=None, limit=50, offset=0)
        assert total == 2
        assert len({r["organization_name"] for r in rows}) >= 2
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_filter_by_seccion():
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P1", seccion="0001")
        _make(db, a1, "P2", seccion="0002")
        rows, total = admin_service.list_admin_registros(db, admin, q=None, lider_id=None,
            activista_id=None, seccion="0001", since=None, until=None, limit=50, offset=0)
        assert total == 1 and rows[0]["seccion"] == "0001"
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_alpha_admin_cannot_see_beta_registros():
    """Negative tenant-isolation: ALPHA admin must not see BETA registros."""
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        alpha_ctx = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        beta_ctx = _camp_ctx(db, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, alpha_ctx, "Alpha Person")
        _make(db, beta_ctx, "Beta Person")
        rows, total = admin_service.list_admin_registros(db, admin, q=None, lider_id=None,
            activista_id=None, seccion=None, since=None, until=None, limit=50, offset=0)
        assert total == 1, f"Expected 1 (only ALPHA), got {total}"
        assert rows[0]["nombre_completo"] == "Alpha Person"
        # Verify the BETA registro is absent
        names = [r["nombre_completo"] for r in rows]
        assert "Beta Person" not in names
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_clave_masked_exposed_raw_enc_absent():
    """Masking assertion: list returns clave_masked, never clave_elector_enc."""
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "Masked Test Person", clave_elector="ABCD1234567890XYZ8")
        rows, total = admin_service.list_admin_registros(db, admin, q=None, lider_id=None,
            activista_id=None, seccion=None, since=None, until=None, limit=50, offset=0)
        assert total == 1
        row = rows[0]
        assert "clave_elector_enc" not in row, "Raw encrypted bytes must not be in listing response"
        assert row["clave_masked"] is not None, "clave_masked should be populated when clave was provided"
        assert row["clave_masked"].startswith("****-"), f"Expected masked format, got: {row['clave_masked']}"
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
