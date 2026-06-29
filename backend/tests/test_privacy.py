"""TDD: PrivacyNotice + PrivacyAcceptance models (SPA-4 Task 2, AC-7.2)."""
from __future__ import annotations


def test_privacy_notice_importable():
    from app.models.privacy import PrivacyAcceptance, PrivacyNotice  # noqa: F401


def test_privacy_notice_columns():
    from app.models.privacy import PrivacyNotice

    cols = {c.name for c in PrivacyNotice.__table__.c}
    assert "organization_id" in cols
    assert "version" in cols
    assert "body" in cols
    assert "is_active" in cols


def test_privacy_acceptance_columns():
    from app.models.privacy import PrivacyAcceptance

    cols = {c.name for c in PrivacyAcceptance.__table__.c}
    assert "registro_id" in cols
    assert "notice_id" in cols
    assert "aviso_version" in cols


def test_privacy_notice_in_metadata():
    from app.database import Base

    import app.models  # noqa: F401

    assert "privacy_notices" in Base.metadata.tables


def test_privacy_acceptance_in_metadata():
    from app.database import Base

    import app.models  # noqa: F401

    assert "privacy_acceptances" in Base.metadata.tables


def test_privacy_notice_organization_id_nullable():
    """organization_id=None marks a global (platform-level) aviso."""
    from app.models.privacy import PrivacyNotice

    col = PrivacyNotice.__table__.c["organization_id"]
    assert col.nullable


def test_global_v1_notice_seeded(seed_data):
    """conftest seed_data creates the global v1 notice (org=None, is_active=True)."""
    from sqlalchemy import select

    from app.models.privacy import PrivacyNotice
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        notice = db.execute(
            select(PrivacyNotice).where(
                PrivacyNotice.organization_id.is_(None),
                PrivacyNotice.version == "v1",
            )
        ).scalar_one_or_none()
        assert notice is not None, "Global v1 notice not found in test DB"
        assert notice.is_active is True
        assert notice.body, "Notice body must be non-empty"
    finally:
        db.close()
