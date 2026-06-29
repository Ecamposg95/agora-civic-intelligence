"""Tests for retention_service.purge_expired (AC-7.4).

TDD: tests written before the implementation.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.campaign import Campaign, Contest
from app.models.catalog import Ambito, Cargo
from app.models.organization import Organization
from app.models.registro import Registro
from tests.conftest import TestingSessionLocal

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_NOW = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
_TODAY = _NOW.date()

# Campaign IDs used by retention tests — distinct from conftest ALPHA/BETA IDs
_RET_CAMPAIGN_PAST = "aaaaaaaa-aaaa-aaaa-aaaa-000000000001"
_RET_CAMPAIGN_FUTURE = "aaaaaaaa-aaaa-aaaa-aaaa-000000000002"
_RET_CAMPAIGN_NO_ELECTION = "aaaaaaaa-aaaa-aaaa-aaaa-000000000003"


def _get_alpha_org_id() -> str:
    db = TestingSessionLocal()
    try:
        org = db.execute(select(Organization).where(Organization.slug == "alpha")).scalar_one()
        return org.id
    finally:
        db.close()


def _get_cargo_id() -> str:
    db = TestingSessionLocal()
    try:
        cargo = db.execute(select(Cargo).where(Cargo.key == "gubernatura")).scalar_one()
        return cargo.id
    finally:
        db.close()


def _make_registro(db, campaign_id: str, org_id: str, deleted_at=None) -> Registro:
    reg = Registro(
        organization_id=org_id,
        campaign_id=campaign_id,
        nombre_completo="Test Persona",
        consentimiento=True,
        consentimiento_at=_NOW,
        aviso_version="v1",
        deleted_at=deleted_at,
    )
    db.add(reg)
    return reg


def _cleanup(db):
    """Remove all retention-test data (campaigns, contests, registros, audit)."""
    campaign_ids = [_RET_CAMPAIGN_PAST, _RET_CAMPAIGN_FUTURE, _RET_CAMPAIGN_NO_ELECTION]
    db.query(Registro).filter(Registro.campaign_id.in_(campaign_ids)).delete(synchronize_session=False)
    db.query(Contest).filter(Contest.campaign_id.in_(campaign_ids)).delete(synchronize_session=False)
    db.query(Campaign).filter(Campaign.id.in_(campaign_ids)).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.action == "retention.purge").delete(synchronize_session=False)
    db.commit()


def _setup_campaigns(db, org_id: str, cargo_id: str):
    """Create three campaigns with different election-date scenarios."""
    # Campaign 1: election_date = 300 days ago → past 180-day retention window
    past_election = _TODAY - timedelta(days=300)
    db.add(Campaign(id=_RET_CAMPAIGN_PAST, name="Past Election", cycle=2024, organization_id=org_id))
    db.flush()
    db.add(Contest(
        campaign_id=_RET_CAMPAIGN_PAST,
        organization_id=org_id,
        cargo_id=cargo_id,
        election_date=past_election,
    ))

    # Campaign 2: election_date = 100 days ago → inside 180-day retention window (NOT eligible)
    recent_election = _TODAY - timedelta(days=100)
    db.add(Campaign(id=_RET_CAMPAIGN_FUTURE, name="Recent Election", cycle=2025, organization_id=org_id))
    db.flush()
    db.add(Contest(
        campaign_id=_RET_CAMPAIGN_FUTURE,
        organization_id=org_id,
        cargo_id=cargo_id,
        election_date=recent_election,
    ))

    # Campaign 3: no election_date → never eligible for post-election purge
    db.add(Campaign(id=_RET_CAMPAIGN_NO_ELECTION, name="No Election", cycle=2026, organization_id=org_id))
    db.flush()
    db.add(Contest(
        campaign_id=_RET_CAMPAIGN_NO_ELECTION,
        organization_id=org_id,
        cargo_id=cargo_id,
        election_date=None,  # explicitly no date
    ))

    db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_noop_when_retention_disabled():
    """When RETENTION_ENABLED=False the service returns immediately with zero counts."""
    from app.services.retention_service import purge_expired
    from app.core.config import settings as app_settings

    org_id = _get_alpha_org_id()
    db = TestingSessionLocal()
    try:
        # Create a very old soft-deleted registro
        reg = _make_registro(
            db, _RET_CAMPAIGN_PAST, org_id,
            deleted_at=_NOW - timedelta(days=365),
        )
        db.commit()
        reg_id = reg.id

        with patch.object(app_settings, "RETENTION_ENABLED", False):
            result = purge_expired(db, now=_NOW)

        assert result.soft_deleted_purged == 0
        assert result.post_election_purged == 0
        assert result.total_purged == 0

        # Row must still exist
        still_there = db.get(Registro, reg_id)
        assert still_there is not None
    finally:
        db.query(Registro).filter(Registro.campaign_id == _RET_CAMPAIGN_PAST).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_purge_soft_deleted_older_than_cutoff():
    """Only soft-deleted rows older than RETENTION_PURGE_SOFT_DELETED_DAYS are hard-purged."""
    from app.services.retention_service import purge_expired
    from app.core.config import settings as app_settings

    org_id = _get_alpha_org_id()
    db = TestingSessionLocal()
    try:
        # Eligible: deleted_at = 60 days ago (> 30-day cutoff)
        old_reg = _make_registro(
            db, _RET_CAMPAIGN_PAST, org_id,
            deleted_at=_NOW - timedelta(days=60),
        )
        # Not eligible: deleted_at = 10 days ago (< 30-day cutoff)
        new_reg = _make_registro(
            db, _RET_CAMPAIGN_PAST, org_id,
            deleted_at=_NOW - timedelta(days=10),
        )
        # Not eligible: NOT soft-deleted (deleted_at is None)
        active_reg = _make_registro(db, _RET_CAMPAIGN_PAST, org_id, deleted_at=None)
        db.commit()
        old_id = old_reg.id
        new_id = new_reg.id
        active_id = active_reg.id

        with patch.object(app_settings, "RETENTION_ENABLED", True), \
             patch.object(app_settings, "RETENTION_PURGE_SOFT_DELETED_DAYS", 30), \
             patch.object(app_settings, "RETENTION_DAYS_AFTER_ELECTION", 180):
            result = purge_expired(db, now=_NOW)

        assert result.soft_deleted_purged == 1, f"expected 1 got {result.soft_deleted_purged}"

        # old registro must be gone
        db.expire_all()
        assert db.get(Registro, old_id) is None, "old soft-deleted registro should have been purged"
        # newer soft-deleted row must survive
        assert db.get(Registro, new_id) is not None, "recent soft-deleted registro must survive"
        # active row must survive
        assert db.get(Registro, active_id) is not None, "active registro must survive"
    finally:
        db.query(Registro).filter(Registro.campaign_id == _RET_CAMPAIGN_PAST).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_post_election_purge_eligible_and_ineligible():
    """Post-election purge removes registros for expired campaigns; ineligible campaigns survive."""
    from app.services.retention_service import purge_expired
    from app.core.config import settings as app_settings

    org_id = _get_alpha_org_id()
    cargo_id = _get_cargo_id()
    db = TestingSessionLocal()
    try:
        _setup_campaigns(db, org_id, cargo_id)

        # Create registros for all three campaigns
        past_reg = _make_registro(db, _RET_CAMPAIGN_PAST, org_id)
        recent_reg = _make_registro(db, _RET_CAMPAIGN_FUTURE, org_id)
        no_election_reg = _make_registro(db, _RET_CAMPAIGN_NO_ELECTION, org_id)
        db.commit()
        past_id = past_reg.id
        recent_id = recent_reg.id
        no_election_id = no_election_reg.id

        with patch.object(app_settings, "RETENTION_ENABLED", True), \
             patch.object(app_settings, "RETENTION_PURGE_SOFT_DELETED_DAYS", 30), \
             patch.object(app_settings, "RETENTION_DAYS_AFTER_ELECTION", 180):
            result = purge_expired(db, now=_NOW)

        assert result.post_election_purged == 1, f"expected 1 post-election purge, got {result.post_election_purged}"
        assert _RET_CAMPAIGN_PAST in result.campaigns_purged

        db.expire_all()
        # Past-election registro must be gone
        assert db.get(Registro, past_id) is None, "past-election registro must have been purged"
        # Recent-election registro must survive
        assert db.get(Registro, recent_id) is not None, "recent-election registro must survive"
        # No-election registro must survive (never eligible)
        assert db.get(Registro, no_election_id) is not None, "no-election registro must survive"
    finally:
        _cleanup(db)
        db.close()


def test_audit_entry_written_after_purge():
    """An audit log entry with action='retention.purge' is written after a purge."""
    from app.services.retention_service import purge_expired
    from app.core.config import settings as app_settings

    org_id = _get_alpha_org_id()
    db = TestingSessionLocal()
    try:
        old_reg = _make_registro(
            db, _RET_CAMPAIGN_PAST, org_id,
            deleted_at=_NOW - timedelta(days=60),
        )
        db.commit()

        # Clear any pre-existing retention.purge audit entries
        db.query(AuditLog).filter(AuditLog.action == "retention.purge").delete(synchronize_session=False)
        db.commit()

        with patch.object(app_settings, "RETENTION_ENABLED", True), \
             patch.object(app_settings, "RETENTION_PURGE_SOFT_DELETED_DAYS", 30), \
             patch.object(app_settings, "RETENTION_DAYS_AFTER_ELECTION", 180):
            result = purge_expired(db, now=_NOW)

        assert result.soft_deleted_purged >= 1

        db.expire_all()
        audit_entries = db.execute(
            select(AuditLog).where(AuditLog.action == "retention.purge")
        ).scalars().all()
        assert len(audit_entries) >= 1, "at least one retention.purge audit entry expected"

        # Audit must not contain PII — check meta has only safe keys
        for entry in audit_entries:
            if entry.meta:
                assert "nombre_completo" not in entry.meta
                assert "telefono" not in entry.meta
                assert "clave_elector" not in entry.meta
    finally:
        db.query(Registro).filter(Registro.campaign_id == _RET_CAMPAIGN_PAST).delete(synchronize_session=False)
        db.query(AuditLog).filter(AuditLog.action == "retention.purge").delete(synchronize_session=False)
        db.commit()
        db.close()


def test_idempotent_second_run_is_noop():
    """Running purge_expired twice: the second call deletes nothing."""
    from app.services.retention_service import purge_expired
    from app.core.config import settings as app_settings

    org_id = _get_alpha_org_id()
    cargo_id = _get_cargo_id()
    db = TestingSessionLocal()
    try:
        _setup_campaigns(db, org_id, cargo_id)
        _make_registro(db, _RET_CAMPAIGN_PAST, org_id)
        _make_registro(
            db, _RET_CAMPAIGN_PAST, org_id,
            deleted_at=_NOW - timedelta(days=60),
        )
        db.commit()

        settings_patch = dict(
            RETENTION_ENABLED=True,
            RETENTION_PURGE_SOFT_DELETED_DAYS=30,
            RETENTION_DAYS_AFTER_ELECTION=180,
        )

        with patch.object(app_settings, "RETENTION_ENABLED", True), \
             patch.object(app_settings, "RETENTION_PURGE_SOFT_DELETED_DAYS", 30), \
             patch.object(app_settings, "RETENTION_DAYS_AFTER_ELECTION", 180):
            first = purge_expired(db, now=_NOW)
            second = purge_expired(db, now=_NOW)

        assert first.total_purged > 0, "first run should have purged something"
        assert second.total_purged == 0, "second run must be a no-op"
    finally:
        _cleanup(db)
        db.close()


def test_dry_run_reports_but_does_not_delete():
    """dry_run=True reports expected counts without deleting any rows."""
    from app.services.retention_service import purge_expired
    from app.core.config import settings as app_settings

    org_id = _get_alpha_org_id()
    db = TestingSessionLocal()
    try:
        reg = _make_registro(
            db, _RET_CAMPAIGN_PAST, org_id,
            deleted_at=_NOW - timedelta(days=60),
        )
        db.commit()
        reg_id = reg.id

        with patch.object(app_settings, "RETENTION_ENABLED", True), \
             patch.object(app_settings, "RETENTION_PURGE_SOFT_DELETED_DAYS", 30), \
             patch.object(app_settings, "RETENTION_DAYS_AFTER_ELECTION", 180):
            result = purge_expired(db, now=_NOW, dry_run=True)

        assert result.dry_run is True
        assert result.soft_deleted_purged >= 1, "dry_run should still report eligible count"

        # Row must still exist (no deletion happened)
        db.expire_all()
        assert db.get(Registro, reg_id) is not None, "dry_run must not delete the row"

        # No audit entry should have been written
        audit_entries = db.execute(
            select(AuditLog).where(AuditLog.action == "retention.purge")
        ).scalars().all()
        assert len(audit_entries) == 0, "dry_run must not write audit entries"
    finally:
        db.query(Registro).filter(Registro.campaign_id == _RET_CAMPAIGN_PAST).delete(synchronize_session=False)
        db.query(AuditLog).filter(AuditLog.action == "retention.purge").delete(synchronize_session=False)
        db.commit()
        db.close()
