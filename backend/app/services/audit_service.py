"""Audit service — append-only trail writes (Golden Rule #5).

Call ``record_audit`` for sensitive reads/writes. The caller controls the
transaction boundary (commit). Never store secrets or raw PII in ``meta``.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    actor_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Append an audit entry to the session (does not commit)."""
    entry = AuditLog(
        action=action,
        actor_id=actor_id,
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        meta=meta,
    )
    db.add(entry)
    return entry
