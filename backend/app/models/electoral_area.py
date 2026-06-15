"""Electoral / territorial area model with PostGIS geometry.

A single generic geometry column holds points (precincts), polygons (districts)
and multipolygons (regions), all in SRID 4326 (WGS84). On non-PostGIS engines
(e.g. SQLite in tests) the column degrades to text so the schema stays portable.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any, Optional

from geoalchemy2 import Geometry
from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import AuditMixin, TenantMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class AreaLevel(str, enum.Enum):
    """Administrative / electoral hierarchy levels."""

    COUNTRY = "country"
    REGION = "region"
    STATE = "state"
    MUNICIPALITY = "municipality"
    DISTRICT = "district"
    PRECINCT = "precinct"


# PostGIS geometry on Postgres; plain text elsewhere (keeps tests portable).
_GEOMETRY_TYPE = Geometry(geometry_type="GEOMETRY", srid=4326).with_variant(
    Text(), "sqlite"
)


class ElectoralArea(UUIDMixin, TenantMixin, AuditMixin, Base):
    """A geospatial civic/electoral unit (tenant-scoped)."""

    __tablename__ = "electoral_areas"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(120), index=True, nullable=True)
    level: Mapped[AreaLevel] = mapped_column(
        Enum(AreaLevel, name="area_level"), default=AreaLevel.DISTRICT, nullable=False
    )

    geometry: Mapped[Optional[Any]] = mapped_column(_GEOMETRY_TYPE, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="electoral_areas")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ElectoralArea id={self.id} name={self.name!r} level={self.level}>"
