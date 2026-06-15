"""Append-only audit log for privacy-by-design and accountability.

Sensitive reads/writes write an immutable record here. There are no update or
delete paths — entries are created and retained.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin

# JSONB on Postgres, generic JSON elsewhere.
_JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class AuditLog(UUIDMixin, Base):
    """Immutable audit trail entry (append-only)."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(36), index=True, nullable=True
    )

    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Attribute is ``meta`` to avoid clashing with SQLAlchemy's ``metadata``;
    # the column itself is named ``metadata``.
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", _JSON_TYPE, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog id={self.id} action={self.action!r} actor={self.actor_id}>"
