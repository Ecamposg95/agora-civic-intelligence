"""Privacy notice versioning + acceptance trail (SPA-4, AC-7.2).

PrivacyNotice  — versioned aviso de privacidad.
               organization_id=NULL  → global (platform-level) aviso,
               organization_id=<id> → tenant-specific override.

PrivacyAcceptance — immutable acceptance record per Registro.
               Links registro_id → notice_id and stores the textual
               aviso_version string for human-readable audit trails.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin, new_uuid


class PrivacyNotice(UUIDMixin, Base):
    """Versioned aviso de privacidad.

    A NULL organization_id means the notice is the global platform default.
    A non-NULL organization_id pins the notice to a specific tenant.

    The UniqueConstraint on (organization_id, version) prevents duplicate
    versions within the same scope (per-tenant or global, on PostgreSQL where
    NULL != NULL the constraint does not prevent two global rows with the same
    version — the seed guards this idempotently).
    """

    __tablename__ = "privacy_notices"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "version",
            name="uq_privacy_notices_org_version",
        ),
        Index("ix_privacy_notices_org_active", "organization_id", "is_active"),
    )

    # nullable so organization_id=None represents the global aviso
    organization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PrivacyAcceptance(UUIDMixin, Base):
    """Immutable acceptance record — one row per (Registro, PrivacyNotice).

    Cascade-deletes with the Registro so that hard-deleting a registro also
    removes its acceptance trail (GDPR right-to-erasure compatible).
    """

    __tablename__ = "privacy_acceptances"

    registro_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("registros.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notice_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("privacy_notices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Denormalised human-readable version string for audit queries without JOIN.
    aviso_version: Mapped[str] = mapped_column(String(40), nullable=False)

    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
