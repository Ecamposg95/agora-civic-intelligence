"""Tests for admin_service.estructura — árbol líder→activistas con conteos."""
from app.models.registro import Registro
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
