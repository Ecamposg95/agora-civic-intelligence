"""Militante — formal party-member affiliation (encrypted PII + doc keys)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON,
    LargeBinary, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import AuditMixin, CampaignMixin, TenantMixin, UUIDMixin


class Militante(UUIDMixin, TenantMixin, CampaignMixin, AuditMixin, Base):
    __tablename__ = "militantes"
    __table_args__ = (
        Index("ix_militantes_campaign_activista", "campaign_id", "activista_id"),
        Index("ix_militantes_campaign_seccion", "campaign_id", "seccion"),
        Index("ix_militantes_campaign_estado", "campaign_id", "estado"),
        UniqueConstraint("campaign_id", "folio", name="uq_militantes_campaign_folio"),
        UniqueConstraint("campaign_id", "activista_id", "client_uuid",
                         name="uq_militantes_campaign_activista_client_uuid"),
    )

    activista_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    sexo: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    fecha_nacimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    seccion: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    calle_numero: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    colonia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cp: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    municipio: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    estado_domicilio: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    es_activista: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estructura: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    promotor: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)

    folio: Mapped[str] = mapped_column(String(40), nullable=False)
    folio_externo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    fecha_afiliacion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    curp_enc: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    curp_masked: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    clave_elector_enc: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    clave_masked: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    credencial_frente_key: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    credencial_reverso_key: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    firma_key: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="REGISTRADO")
    validado_por: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validado_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    observacion_validacion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    quality_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    consentimiento: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consentimiento_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    aviso_version: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    manifestacion_voluntad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    client_uuid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
