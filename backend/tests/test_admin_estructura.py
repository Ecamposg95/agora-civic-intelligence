"""Tests for admin_service.estructura — árbol líder→activistas con conteos."""
from sqlalchemy import select

from app.models.registro import Registro
from app.models.user import User, UserRole
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID, BETA_CAMPAIGN_ID


def test_estructura_tree_counts():
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx, _make
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P1")
        tree = admin_service.estructura(db, admin)
        # lider@alpha.gov has activista1 + activista2 under them
        lider_node = next(n for n in tree if n["full_name"] == "Alpha Líder")
        activista_names = {a["full_name"] for a in lider_node["activistas"]}
        assert {"Alpha Activista 1", "Alpha Activista 2"} <= activista_names
        a1_node = next(a for a in lider_node["activistas"] if a["full_name"] == "Alpha Activista 1")
        assert a1_node["count"] == 1
        # Node rollup: total equals sum of activistas' counts
        expected_total = sum(a["count"] for a in lider_node["activistas"])
        assert lider_node["total"] == expected_total
        assert lider_node["total"] >= 1  # non-vacuous: at least 1 registro in tree
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_estructura_zero_count_for_activista_without_registros():
    """Activistas with no registros still appear in the tree with count=0."""
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx
    db = TestingSessionLocal()
    try:
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        tree = admin_service.estructura(db, admin)
        lider_node = next(n for n in tree if n["full_name"] == "Alpha Líder")
        a2_node = next(a for a in lider_node["activistas"] if a["full_name"] == "Alpha Activista 2")
        assert a2_node["count"] == 0
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_estructura_lider_scope():
    """A lider context sees only their own subtree."""
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx
    db = TestingSessionLocal()
    try:
        lider = _camp_ctx(db, "lider@alpha.gov", ALPHA_CAMPAIGN_ID)
        tree = admin_service.estructura(db, lider)
        # Only the lider themselves in the tree
        assert len(tree) == 1
        assert tree[0]["full_name"] == "Alpha Líder"
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_estructura_tenant_isolation():
    """Admin from alpha only sees alpha's structure."""
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx
    db = TestingSessionLocal()
    try:
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        tree = admin_service.estructura(db, admin)
        emails = {n["email"] for n in tree}
        # No beta lider should appear
        assert "lider@beta.gov" not in emails
        # All nodes belong to alpha
        for node in tree:
            assert "alpha" in node["email"] or "alpha" in (node.get("full_name") or "")
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_estructura_activistas_org_filter():
    """Activistas sub-query must exclude cross-tenant users even if lider_id matches.

    This guards against a data-integrity violation where an activista from org B
    has a lider_id pointing at a lider in org A.  The estructura tree for org A
    must not surface the alien activista.
    """
    from app.core.security import hash_password
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx
    db = TestingSessionLocal()
    try:
        # Find alpha's lider and beta's org
        alpha_lider = db.execute(
            select(User).where(User.email == "lider@alpha.gov")
        ).scalar_one()
        beta_activista_row = db.execute(
            select(User).where(User.email == "activista_beta@beta.gov")
        ).scalar_one()

        # Simulate a data-integrity violation: beta activista's lider_id
        # points at alpha's lider.
        original_lider_id = beta_activista_row.lider_id
        beta_activista_row.lider_id = alpha_lider.id
        db.flush()

        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        tree = admin_service.estructura(db, admin)

        # Beta's activista must NOT appear under alpha's lider node.
        lider_node = next((n for n in tree if n["email"] == "lider@alpha.gov"), None)
        assert lider_node is not None
        activista_emails = {a["email"] for a in lider_node["activistas"]}
        assert "activista_beta@beta.gov" not in activista_emails

        # Restore to avoid poisoning other tests.
        beta_activista_row.lider_id = original_lider_id
        db.commit()
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
