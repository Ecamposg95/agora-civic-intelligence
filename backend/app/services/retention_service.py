"""Data retention / purge service (AC-7.4).

Election-date resolution
------------------------
A Registro is eligible for post-election purge when its campaign's **latest
non-NULL** ``Contest.election_date`` plus ``RETENTION_DAYS_AFTER_ELECTION``
days has passed.  Registros whose campaign has no Contest with a non-NULL
election_date are **never** eligible for Pass B — they are only subject to
Pass A (soft-delete age).

Two passes per run
------------------
Pass A — soft-delete purge
    Hard-delete rows where ``deleted_at`` < ``now - RETENTION_PURGE_SOFT_DELETED_DAYS``.

Pass B — post-election purge
    Hard-delete all remaining rows (active or soft-deleted) for campaigns
    whose max(election_date) <= today - RETENTION_DAYS_AFTER_ELECTION.

Safety guarantees
-----------------
* NO-OP when ``RETENTION_ENABLED=False`` (default).
* ``dry_run=True`` reports counts without touching the database.
* Idempotent: re-running on an already-purged dataset produces zero deletes.
* Audit records written per pass (Pass A and Pass B separately).
* No PII is written to audit logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.campaign import Contest
from app.models.registro import Registro
from app.services.audit_service import record_audit


@dataclass
class PurgeResult:
    """Counts and metadata from a single retention run."""

    soft_deleted_purged: int = 0
    post_election_purged: int = 0
    campaigns_purged: List[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total_purged(self) -> int:
        """Total rows hard-deleted (or that would be deleted in dry_run)."""
        return self.soft_deleted_purged + self.post_election_purged


def _coerce_date(value) -> Optional[date_type]:
    """Normalize a DB-returned date value to a Python date.

    SQLite returns Date columns as Python date objects, but func.max() may
    return a string in ISO format on some backends.  Handle both.
    """
    if value is None:
        return None
    if isinstance(value, date_type):
        return value
    try:
        return date_type.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def purge_expired(
    db: Session,
    *,
    now: Optional[datetime] = None,
    dry_run: bool = False,
) -> PurgeResult:
    """Purge expired registros according to the configured retention policy.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.  The caller owns the session lifecycle.
    now:
        Reference timestamp for cutoff calculations (defaults to UTC now).
        Useful for testing with a fixed point in time.
    dry_run:
        When True, compute and return counts without modifying the database.

    Returns
    -------
    PurgeResult
        Counts per pass and list of purged campaign IDs.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    result = PurgeResult(dry_run=dry_run)

    # ── Safety gate ───────────────────────────────────────────────────────────
    if not settings.RETENTION_ENABLED:
        return result

    today: date_type = now.date() if isinstance(now, datetime) else now  # type: ignore[arg-type]

    # ── Pass A: hard-delete soft-deleted rows past their grace period ─────────
    soft_cutoff: datetime = now - timedelta(days=settings.RETENTION_PURGE_SOFT_DELETED_DAYS)

    soft_filter = (
        Registro.deleted_at.is_not(None),
        Registro.deleted_at < soft_cutoff,
    )

    soft_count: int = db.scalar(
        select(func.count(Registro.id)).where(*soft_filter)
    ) or 0

    if not dry_run and soft_count > 0:
        db.execute(delete(Registro).where(*soft_filter))
        record_audit(
            db,
            action="retention.purge",
            entity_type="registro",
            meta={
                "pass": "soft_deleted",
                "count": soft_count,
                "cutoff_days": settings.RETENTION_PURGE_SOFT_DELETED_DAYS,
            },
        )

    result.soft_deleted_purged = soft_count

    # ── Pass B: post-election purge ───────────────────────────────────────────
    # Eligible: max(election_date) + RETENTION_DAYS_AFTER_ELECTION <= today
    #         ≡ max(election_date) <= today - RETENTION_DAYS_AFTER_ELECTION
    election_cutoff: date_type = today - timedelta(days=settings.RETENTION_DAYS_AFTER_ELECTION)

    campaign_max_rows = db.execute(
        select(Contest.campaign_id, func.max(Contest.election_date).label("max_date"))
        .where(Contest.election_date.is_not(None))
        .group_by(Contest.campaign_id)
    ).all()

    eligible_campaign_ids: list[str] = [
        row.campaign_id
        for row in campaign_max_rows
        if _coerce_date(row.max_date) is not None
        and _coerce_date(row.max_date) <= election_cutoff  # type: ignore[operator]
    ]

    post_count = 0
    if eligible_campaign_ids:
        post_filter = Registro.campaign_id.in_(eligible_campaign_ids)

        post_count = db.scalar(
            select(func.count(Registro.id)).where(post_filter)
        ) or 0

        if not dry_run and post_count > 0:
            db.execute(delete(Registro).where(post_filter))
            record_audit(
                db,
                action="retention.purge",
                entity_type="campaign",
                meta={
                    "pass": "post_election",
                    "count": post_count,
                    "campaign_ids": eligible_campaign_ids,
                    "cutoff_days": settings.RETENTION_DAYS_AFTER_ELECTION,
                },
            )

    result.post_election_purged = post_count
    result.campaigns_purged = list(eligible_campaign_ids)

    # ── Commit (single transaction for both passes) ───────────────────────────
    if not dry_run and result.total_purged > 0:
        db.commit()

    return result
