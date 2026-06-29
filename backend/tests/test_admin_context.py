"""Tests for get_admin_context: consolidated superadmin vs base-scoped."""
from sqlalchemy import select

from app.dependencies import TenantContext, get_admin_context
from app.models.user import User
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID


def test_superadmin_no_base_is_consolidated(seed_data):
    """Superadmin without X-Campaign-Id header → consolidated mode (org None, camp "")."""
    db = TestingSessionLocal()
    try:
        su = db.execute(select(User).where(User.email == "super@atlas.gov")).scalar_one()
        tctx = TenantContext(user=su, organization_id=None, role=su.role)
        ctx = get_admin_context(db, tctx, None)
        assert ctx.organization_id is None
        assert ctx.campaign_id == ""
        assert ctx.is_superadmin
    finally:
        db.close()


def test_superadmin_with_base_adopts_org(seed_data):
    """Superadmin WITH X-Campaign-Id → base-scoped, org adopted from campaign."""
    db = TestingSessionLocal()
    try:
        su = db.execute(select(User).where(User.email == "super@atlas.gov")).scalar_one()
        tctx = TenantContext(user=su, organization_id=None, role=su.role)
        ctx = get_admin_context(db, tctx, ALPHA_CAMPAIGN_ID)
        assert ctx.organization_id is not None  # adopted from the campaign's org
        assert ctx.campaign_id == ALPHA_CAMPAIGN_ID
        assert ctx.is_superadmin
    finally:
        db.close()


def test_normal_admin_with_base_is_scoped(seed_data):
    """Normal ADMIN with X-Campaign-Id → campaign-scoped context."""
    db = TestingSessionLocal()
    try:
        admin = db.execute(select(User).where(User.email == "admin@alpha.gov")).scalar_one()
        tctx = TenantContext(user=admin, organization_id=admin.organization_id, role=admin.role)
        ctx = get_admin_context(db, tctx, ALPHA_CAMPAIGN_ID)
        assert ctx.organization_id == admin.organization_id
        assert ctx.campaign_id == ALPHA_CAMPAIGN_ID
        assert not ctx.is_superadmin
    finally:
        db.close()
