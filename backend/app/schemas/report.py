"""Report schemas — aggregated views with NO PII (AC-8.3)."""
from __future__ import annotations

from pydantic import BaseModel


class SeccionReportItem(BaseModel):
    """A single seccion bucket: label + count only, no PII."""
    seccion: str  # "Sin sección" when Registro.seccion is NULL
    count: int


class SeccionReport(BaseModel):
    """Aggregated report by electoral section."""
    total: int
    items: list[SeccionReportItem]
