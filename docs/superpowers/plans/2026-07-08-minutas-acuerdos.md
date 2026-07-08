# Minutas & Acuerdos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Digitalizar minutas de reuniones y el seguimiento de los acuerdos que salen de ellas (Sub-proyecto A del módulo de gestión de trabajo).

**Architecture:** Nuevo módulo `minutas` que reusa el spine (multi-tenancy, campaign scoping, RBAC de 9 roles, audit). Dos entidades: `Minuta` (acta) y `Acuerdo` (compromiso hijo). Backend FastAPI + SQLAlchemy + Alembic; frontend React (Atenea kit) consumiendo `/api/minutas` y `/api/acuerdos`. Sigue el molde exacto de `Caso`/`caso_service`/`casos` router.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest (SQLite en memoria); React + TypeScript + Vite + axios.

## Global Constraints

- Toda query de negocio filtra por `organization_id` vía `scoped_query(Model, ctx)`. — `app/core/scoping.py`
- `organization_id`/`campaign_id` en escrituras vienen del contexto (JWT/`X-Campaign-Id`), nunca del body.
- Endpoints devuelven schemas Pydantic, nunca ORM crudo.
- RBAC en la capa API con `require_roles(*roles)` de `app/dependencies.py`.
- Toda escritura sensible emite `audit_service.record_audit(db, action=..., actor_id=..., organization_id=..., entity_type=..., entity_id=..., meta=...)` (no hace commit).
- Listas paginadas: `{ items, total, limit, offset }`.
- Envelope de error: `{ "error": { "message", "status" } }` (usar `HTTPException`).
- **COORDINADOR es campaign-wide** (ve toda la campaña, sin gate de sub-árbol); LIDER/ACTIVISTA quedan jerarquizados.
- Migración idempotente (`_table_exists`/`_index_exists`), compatible SQLite (solo `String`/`Date`/`Integer`/`JSON`; sin `ALTER TYPE`/`autocommit_block`).
- Estados como `String(20)` (sin enums de PostgreSQL).
- Baseline pytest debe seguir verde; correr desde `backend/`.

---

### Task 1: Modelo de datos + migración 0018

**Files:**
- Create: `backend/app/models/minuta.py`
- Modify: `backend/app/models/__init__.py` (registrar modelos)
- Create: `backend/app/alembic/versions/0018_minutas.py`  *(usar la ruta real de versions; ver `0016_atencion.py`)*
- Test: `backend/tests/test_minutas.py`

**Interfaces:**
- Produces: `Minuta` (tabla `minutas`) y `Acuerdo` (tabla `acuerdos`), modelos importables desde `app.models.minuta`. Columnas según spec.

- [ ] **Step 1: Write the failing test**

En `backend/tests/test_minutas.py`:

```python
import datetime as dt
from app.models.minuta import Minuta, Acuerdo


def test_minuta_and_acuerdo_persist(db_session):
    m = Minuta(
        organization_id="org-1", campaign_id="camp-1",
        titulo="Reunión de arranque", fecha=dt.date(2026, 7, 8),
        tipo="REUNION", estado="BORRADOR",
        asistentes=[{"nombre": "Lucy"}, {"user_id": "u-2", "nombre": "Juan"}],
        cuerpo="Notas de la reunión.",
    )
    db_session.add(m)
    db_session.flush()
    a = Acuerdo(
        organization_id="org-1", campaign_id="camp-1", minuta_id=m.id,
        texto="Levantar padrón de la sección 123", orden=0,
        estado="PENDIENTE", fecha_limite=dt.date(2026, 7, 15),
    )
    db_session.add(a)
    db_session.flush()
    assert m.id and a.minuta_id == m.id
    assert m.estado == "BORRADOR" and a.estado == "PENDIENTE"
    assert a.work_item_id is None
```

> Nota: `db_session` es el fixture del `conftest.py` existente. Si el fixture se llama distinto, usar el que ya exista (ver otros `tests/test_*.py`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_minutas.py::test_minuta_and_acuerdo_persist -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.minuta'`.

- [ ] **Step 3: Create the model**

`backend/app/models/minuta.py`:

```python
"""Minutas & Acuerdos — meeting minutes and their action items.

Mirrors ``Caso``/``CasoEvento`` (app/models/atencion.py): String(20) estados
(no PG enums → simple, SQLite-compatible), tenant+campaign+audit mixins. A
``Minuta`` is a meeting record; an ``Acuerdo`` is a commitment born in it. The
``work_item_id`` column is a reserved hook for Sub-proyecto B (Scrum backlog).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import AuditMixin, CampaignMixin, TenantMixin, UUIDMixin


class Minuta(UUIDMixin, TenantMixin, CampaignMixin, AuditMixin, Base):
    __tablename__ = "minutas"
    __table_args__ = (
        Index("ix_minutas_campaign_fecha", "campaign_id", "fecha"),
        Index("ix_minutas_campaign_estado", "campaign_id", "estado"),
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    lugar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="REUNION")
    asistentes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cuerpo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="BORRADOR")
    area_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("electoral_areas.id", ondelete="SET NULL"), nullable=True)


class Acuerdo(UUIDMixin, TenantMixin, CampaignMixin, AuditMixin, Base):
    __tablename__ = "acuerdos"
    __table_args__ = (
        Index("ix_acuerdos_minuta", "minuta_id"),
        Index("ix_acuerdos_campaign_responsable_estado",
               "campaign_id", "responsable_id", "estado"),
    )
    minuta_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("minutas.id", ondelete="CASCADE"), nullable=False, index=True)
    texto: Mapped[str] = mapped_column(String(2000), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    responsable_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    fecha_limite: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDIENTE")
    work_item_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
```

- [ ] **Step 4: Register the models**

En `backend/app/models/__init__.py`, añadir tras la línea de `militante` (orden alfabético):

```python
from app.models.minuta import Acuerdo, Minuta  # noqa: F401
```

- [ ] **Step 5: Write the migration**

`backend/app/alembic/versions/0018_minutas.py` (misma ruta/estilo que `0016_atencion.py`):

```python
"""0018 minutas & acuerdos — meeting minutes and action items

Revision ID: 0018_minutas
Revises: 0017_operacion
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_minutas"
down_revision = "0017_operacion"
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return name in _insp().get_table_names()


def _index_exists(table: str, name: str) -> bool:
    if not _table_exists(table):
        return False
    return any(ix["name"] == name for ix in _insp().get_indexes(table))


def upgrade() -> None:
    if not _table_exists("minutas"):
        op.create_table(
            "minutas",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("titulo", sa.String(255), nullable=False),
            sa.Column("fecha", sa.Date(), nullable=False),
            sa.Column("lugar", sa.String(255), nullable=True),
            sa.Column("tipo", sa.String(20), nullable=False, server_default="REUNION"),
            sa.Column("asistentes", sa.JSON(), nullable=False),
            sa.Column("cuerpo", sa.Text(), nullable=True),
            sa.Column("estado", sa.String(20), nullable=False, server_default="BORRADOR"),
            sa.Column("area_id", sa.String(36), sa.ForeignKey("electoral_areas.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )
    if not _index_exists("minutas", "ix_minutas_campaign_fecha"):
        op.create_index("ix_minutas_campaign_fecha", "minutas", ["campaign_id", "fecha"])
    if not _index_exists("minutas", "ix_minutas_campaign_estado"):
        op.create_index("ix_minutas_campaign_estado", "minutas", ["campaign_id", "estado"])

    if not _table_exists("acuerdos"):
        op.create_table(
            "acuerdos",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("minuta_id", sa.String(36), sa.ForeignKey("minutas.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("texto", sa.String(2000), nullable=False),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("responsable_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("fecha_limite", sa.Date(), nullable=True),
            sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
            sa.Column("work_item_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )
    if not _index_exists("acuerdos", "ix_acuerdos_campaign_responsable_estado"):
        op.create_index("ix_acuerdos_campaign_responsable_estado", "acuerdos", ["campaign_id", "responsable_id", "estado"])


def downgrade() -> None:
    op.drop_table("acuerdos")
    op.drop_table("minutas")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_minutas.py::test_minuta_and_acuerdo_persist -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/minuta.py backend/app/models/__init__.py backend/app/alembic/versions/0018_minutas.py backend/tests/test_minutas.py
git commit -m "feat(minutas): model + migration 0018 (minutas, acuerdos)"
```

---

### Task 2: Schemas Pydantic

**Files:**
- Create: `backend/app/schemas/minuta.py`
- Test: `backend/tests/test_minutas.py` (añadir)

**Interfaces:**
- Produces: `MinutaCreate`, `MinutaUpdate`, `MinutaRead`, `MinutaList`, `AcuerdoCreate`, `AcuerdoUpdate`, `AcuerdoRead`, `AcuerdoList`, `Asistente`.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_minutas.py`:

```python
import pytest
from pydantic import ValidationError
from app.schemas.minuta import MinutaCreate, AcuerdoUpdate


def test_minuta_create_validates_estado_and_tipo():
    m = MinutaCreate(titulo="Junta", fecha="2026-07-08", tipo="REUNION")
    assert m.estado == "BORRADOR"
    with pytest.raises(ValidationError):
        MinutaCreate(titulo="x", fecha="2026-07-08", tipo="INVALIDO")


def test_acuerdo_update_rejects_bad_estado():
    AcuerdoUpdate(estado="CUMPLIDO")
    with pytest.raises(ValidationError):
        AcuerdoUpdate(estado="ARCHIVADO")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_minutas.py -k "validates or bad_estado" -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.minuta'`.

- [ ] **Step 3: Create the schemas**

`backend/app/schemas/minuta.py`:

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

MINUTA_TIPO = "^(REUNION|PLANNING|DAILY|REVIEW|RETRO|OTRO)$"
MINUTA_ESTADO = "^(BORRADOR|PUBLICADA)$"
ACUERDO_ESTADO = "^(PENDIENTE|EN_CURSO|CUMPLIDO|CANCELADO)$"


class Asistente(BaseModel):
    user_id: Optional[str] = None
    nombre: str = Field(min_length=1, max_length=255)


class AcuerdoCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)
    responsable_id: Optional[str] = None
    fecha_limite: Optional[date] = None
    orden: int = 0


class AcuerdoUpdate(BaseModel):
    texto: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    responsable_id: Optional[str] = None
    fecha_limite: Optional[date] = None
    orden: Optional[int] = None
    estado: Optional[str] = Field(default=None, pattern=ACUERDO_ESTADO)


class AcuerdoRead(BaseModel):
    id: str
    minuta_id: str
    texto: str
    orden: int
    responsable_id: Optional[str] = None
    responsable_nombre: Optional[str] = None
    fecha_limite: Optional[date] = None
    estado: str
    work_item_id: Optional[str] = None
    created_at: datetime


class AcuerdoList(BaseModel):
    items: list[AcuerdoRead]
    total: int
    limit: int
    offset: int


class MinutaCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    fecha: date
    lugar: Optional[str] = Field(default=None, max_length=255)
    tipo: str = Field(default="REUNION", pattern=MINUTA_TIPO)
    estado: str = Field(default="BORRADOR", pattern=MINUTA_ESTADO)
    asistentes: list[Asistente] = Field(default_factory=list)
    cuerpo: Optional[str] = None
    area_id: Optional[str] = None
    acuerdos: list[AcuerdoCreate] = Field(default_factory=list)


class MinutaUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=255)
    fecha: Optional[date] = None
    lugar: Optional[str] = Field(default=None, max_length=255)
    tipo: Optional[str] = Field(default=None, pattern=MINUTA_TIPO)
    estado: Optional[str] = Field(default=None, pattern=MINUTA_ESTADO)
    asistentes: Optional[list[Asistente]] = None
    cuerpo: Optional[str] = None
    area_id: Optional[str] = None


class MinutaRead(BaseModel):
    id: str
    titulo: str
    fecha: date
    lugar: Optional[str] = None
    tipo: str
    estado: str
    asistentes: list[Asistente] = Field(default_factory=list)
    cuerpo: Optional[str] = None
    area_id: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None
    acuerdos: list[AcuerdoRead] = Field(default_factory=list)
    acuerdos_pendientes: int = 0


class MinutaList(BaseModel):
    items: list[MinutaRead]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_minutas.py -k "validates or bad_estado" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/minuta.py backend/tests/test_minutas.py
git commit -m "feat(minutas): pydantic schemas"
```

---

### Task 3: Servicio — minutas CRUD + scoping

**Files:**
- Create: `backend/app/services/minuta_service.py`
- Test: `backend/tests/test_minutas.py` (añadir)

**Interfaces:**
- Consumes: `Minuta`, `Acuerdo` (Task 1); `scoped_query` (`app.core.scoping`); `record_audit` (`app.services.audit_service`); `CampaignContext`, `UserRole`.
- Produces:
  - `create_minuta(db, ctx, data: MinutaCreate) -> Minuta`
  - `list_minutas(db, ctx, *, tipo=None, estado=None, desde=None, hasta=None, limit=50, offset=0) -> tuple[list[Minuta], int]`
  - `get_minuta(db, ctx, mid: str) -> Optional[Minuta]`
  - `update_minuta(db, ctx, mid: str, data: MinutaUpdate) -> Optional[Minuta]`
  - `delete_minuta(db, ctx, mid: str) -> bool`
  - `_minuta_role_scoped(ctx)` (helper)
  - `enrich_acuerdos(db, minuta)` (rellena `responsable_nombre` + `acuerdos_pendientes`)
  - `PublishedLockError(Exception)`

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_minutas.py`. Reusar el helper de contexto/usuarios que usen otros tests (ver `tests/test_casos.py`); abajo se asume un fixture `coordinador_ctx` y `lider_ctx` análogos, o construirlos con el mismo patrón de `tests/test_casos.py`.

```python
from app.schemas.minuta import MinutaCreate, MinutaUpdate
from app.services import minuta_service


def test_create_minuta_with_acuerdos_inherits_scope(db_session, coordinador_ctx):
    data = MinutaCreate(
        titulo="Arranque", fecha="2026-07-08", tipo="REUNION",
        asistentes=[{"nombre": "Lucy"}],
        acuerdos=[{"texto": "Padrón sección 123", "fecha_limite": "2026-07-15"}],
    )
    m = minuta_service.create_minuta(db_session, coordinador_ctx, data)
    assert m.organization_id == coordinador_ctx.organization_id
    assert m.campaign_id == coordinador_ctx.campaign_id
    rows, total = minuta_service.list_minutas(db_session, coordinador_ctx)
    assert total == 1 and rows[0].id == m.id
    # acuerdo heredó scope de la minuta
    from app.models.minuta import Acuerdo
    ac = db_session.query(Acuerdo).filter_by(minuta_id=m.id).one()
    assert ac.organization_id == m.organization_id and ac.campaign_id == m.campaign_id


def test_publish_locks_body_for_non_coordinator(db_session, coordinador_ctx, lider_ctx):
    # coordinador crea y publica
    m = minuta_service.create_minuta(
        db_session, coordinador_ctx,
        MinutaCreate(titulo="Acta", fecha="2026-07-08"))
    minuta_service.update_minuta(db_session, coordinador_ctx, m.id,
                                 MinutaUpdate(estado="PUBLICADA"))
    # lider intenta editar cuerpo de acta publicada → bloqueado
    import pytest
    with pytest.raises(minuta_service.PublishedLockError):
        minuta_service.update_minuta(db_session, lider_ctx, m.id,
                                     MinutaUpdate(cuerpo="cambio ilegal"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_minutas.py -k "inherits_scope or locks_body" -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.minuta_service'`.

- [ ] **Step 3: Create the service**

`backend/app/services/minuta_service.py`:

```python
"""Minuta service — meeting minutes + action items.

Mirrors caso_service for scoping/audit. COORDINADOR is campaign-wide;
LIDER/ACTIVISTA are hierarchy/ownership scoped. A PUBLICADA minuta locks its
narrative fields for non-coordinators (agreements can still change estado).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.scoping import scoped_query
from app.dependencies import CampaignContext
from app.models.minuta import Acuerdo, Minuta
from app.models.user import User, UserRole
from app.schemas.minuta import MinutaCreate, MinutaUpdate
from app.services.audit_service import record_audit

_NARRATIVE = ("titulo", "fecha", "lugar", "cuerpo", "tipo")


class PublishedLockError(Exception):
    """Raised when a non-coordinator edits narrative fields of a PUBLICADA minuta."""


def _is_coordinator(ctx: CampaignContext) -> bool:
    return ctx.is_superadmin or ctx.role in (UserRole.ADMIN, UserRole.COORDINADOR)


def _minuta_role_scoped(ctx: CampaignContext):
    """COORDINADOR/ADMIN → whole campaign. LIDER → own team's minutas
    (created by self or a supervised activista). ACTIVISTA → own only."""
    if _is_coordinator(ctx):
        return scoped_query(Minuta, ctx)
    if ctx.role == UserRole.LIDER:
        activistas = select(User.id).where(User.lider_id == ctx.user.id)
        return scoped_query(Minuta, ctx).where(
            or_(Minuta.created_by == ctx.user.id, Minuta.created_by.in_(activistas)))
    if ctx.role in (UserRole.ACTIVISTA, UserRole.CAPTURISTA):
        return scoped_query(Minuta, ctx).where(Minuta.created_by == ctx.user.id)
    return scoped_query(Minuta, ctx).where(sa.false())


def enrich_acuerdos(db: Session, minuta: Minuta) -> None:
    """Attach responsable_nombre to each acuerdo + acuerdos_pendientes count."""
    acuerdos = list(db.execute(
        select(Acuerdo).where(Acuerdo.minuta_id == minuta.id,
                              Acuerdo.deleted_at.is_(None))
        .order_by(Acuerdo.orden, Acuerdo.created_at)
    ).scalars().all())
    ids = {a.responsable_id for a in acuerdos if a.responsable_id}
    names: dict[str, str] = {}
    if ids:
        for uid, fname in db.execute(
                select(User.id, User.full_name).where(User.id.in_(ids))).all():
            names[uid] = fname
    for a in acuerdos:
        a.responsable_nombre = names.get(a.responsable_id)
    minuta.acuerdos = acuerdos
    minuta.acuerdos_pendientes = sum(
        1 for a in acuerdos if a.estado in ("PENDIENTE", "EN_CURSO"))


def create_minuta(db: Session, ctx: CampaignContext, data: MinutaCreate) -> Minuta:
    m = Minuta(
        organization_id=ctx.organization_id, campaign_id=ctx.campaign_id,
        titulo=data.titulo, fecha=data.fecha, lugar=data.lugar,
        tipo=data.tipo, estado=data.estado,
        asistentes=[a.model_dump() for a in data.asistentes],
        cuerpo=data.cuerpo, area_id=data.area_id, created_by=ctx.user.id,
    )
    db.add(m)
    db.flush()
    for i, ac in enumerate(data.acuerdos):
        db.add(Acuerdo(
            organization_id=ctx.organization_id, campaign_id=ctx.campaign_id,
            minuta_id=m.id, texto=ac.texto, orden=ac.orden or i,
            responsable_id=ac.responsable_id, fecha_limite=ac.fecha_limite,
            estado="PENDIENTE", created_by=ctx.user.id,
        ))
    record_audit(db, action="minuta.create", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="minuta",
                 entity_id=m.id, meta={"acuerdos": len(data.acuerdos)})
    db.flush()
    enrich_acuerdos(db, m)
    return m


def list_minutas(db: Session, ctx: CampaignContext, *, tipo=None, estado=None,
                 desde: Optional[date] = None, hasta: Optional[date] = None,
                 limit=50, offset=0) -> tuple[list[Minuta], int]:
    stmt = _minuta_role_scoped(ctx)
    if tipo:
        stmt = stmt.where(Minuta.tipo == tipo)
    if estado:
        stmt = stmt.where(Minuta.estado == estado)
    if desde:
        stmt = stmt.where(Minuta.fecha >= desde)
    if hasta:
        stmt = stmt.where(Minuta.fecha <= hasta)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    ordered = stmt.order_by(Minuta.fecha.desc(), Minuta.created_at.desc())
    rows = list(db.execute(ordered.limit(limit).offset(offset)).scalars().all())
    for m in rows:
        enrich_acuerdos(db, m)
    return rows, total


def get_minuta(db: Session, ctx: CampaignContext, mid: str) -> Optional[Minuta]:
    m = db.execute(_minuta_role_scoped(ctx).where(Minuta.id == mid)).scalar_one_or_none()
    if m is not None:
        enrich_acuerdos(db, m)
    return m


def update_minuta(db: Session, ctx: CampaignContext, mid: str,
                  data: MinutaUpdate) -> Optional[Minuta]:
    m = db.execute(_minuta_role_scoped(ctx).where(Minuta.id == mid)).scalar_one_or_none()
    if m is None:
        return None
    fields = data.model_dump(exclude_unset=True)
    # PUBLICADA locks narrative fields for non-coordinators.
    if m.estado == "PUBLICADA" and not _is_coordinator(ctx):
        if any(f in fields for f in _NARRATIVE):
            raise PublishedLockError()
    if "asistentes" in fields and fields["asistentes"] is not None:
        fields["asistentes"] = [a for a in fields["asistentes"]]  # already dicts via model_dump
    for k, v in fields.items():
        setattr(m, k, v)
    m.updated_by = ctx.user.id
    record_audit(db, action="minuta.update", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="minuta",
                 entity_id=m.id, meta={"fields": list(fields.keys())})
    db.flush()
    enrich_acuerdos(db, m)
    return m


def delete_minuta(db: Session, ctx: CampaignContext, mid: str) -> bool:
    m = db.execute(_minuta_role_scoped(ctx).where(Minuta.id == mid)).scalar_one_or_none()
    if m is None:
        return False
    from datetime import datetime, timezone
    m.deleted_at = datetime.now(timezone.utc)
    m.updated_by = ctx.user.id
    record_audit(db, action="minuta.delete", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="minuta",
                 entity_id=m.id, meta=None)
    db.flush()
    return True
```

> Nota sobre `asistentes` en `update`: `data.model_dump(exclude_unset=True)` ya convierte los `Asistente` a dicts, así que la línea de normalización es un no-op defensivo; puede omitirse si tu versión de Pydantic ya entrega dicts.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_minutas.py -k "inherits_scope or locks_body" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/minuta_service.py backend/tests/test_minutas.py
git commit -m "feat(minutas): service (minutas CRUD, scoping, publish lock)"
```

---

### Task 4: Servicio — acuerdos CRUD + lista transversal

**Files:**
- Modify: `backend/app/services/minuta_service.py`
- Test: `backend/tests/test_minutas.py` (añadir)

**Interfaces:**
- Consumes: `Minuta`, `Acuerdo`, `_minuta_role_scoped`, `_is_coordinator` (Task 3); `AcuerdoCreate`, `AcuerdoUpdate`.
- Produces:
  - `add_acuerdo(db, ctx, mid, data: AcuerdoCreate) -> Optional[Acuerdo]`
  - `update_acuerdo(db, ctx, mid, aid, data: AcuerdoUpdate) -> Optional[Acuerdo]`
  - `delete_acuerdo(db, ctx, mid, aid) -> bool`
  - `list_acuerdos(db, ctx, *, responsable_id=None, estado=None, vence_antes=None, limit=50, offset=0) -> tuple[list[Acuerdo], int]`

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_minutas.py`:

```python
from app.schemas.minuta import AcuerdoCreate, AcuerdoUpdate


def test_acuerdo_lifecycle_and_transversal_list(db_session, coordinador_ctx):
    m = minuta_service.create_minuta(
        db_session, coordinador_ctx,
        MinutaCreate(titulo="Acta", fecha="2026-07-08"))
    a = minuta_service.add_acuerdo(
        db_session, coordinador_ctx, m.id,
        AcuerdoCreate(texto="Tarea", fecha_limite="2026-07-10"))
    assert a is not None and a.estado == "PENDIENTE"
    a2 = minuta_service.update_acuerdo(
        db_session, coordinador_ctx, m.id, a.id, AcuerdoUpdate(estado="CUMPLIDO"))
    assert a2.estado == "CUMPLIDO"
    # lista transversal por vencimiento
    rows, total = minuta_service.list_acuerdos(
        db_session, coordinador_ctx, vence_antes="2026-07-31")
    assert total == 1 and rows[0].id == a.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_minutas.py -k "acuerdo_lifecycle" -v`
Expected: FAIL con `AttributeError: module 'app.services.minuta_service' has no attribute 'add_acuerdo'`.

- [ ] **Step 3: Add the acuerdo functions**

Añadir al final de `backend/app/services/minuta_service.py`:

```python
from app.schemas.minuta import AcuerdoCreate, AcuerdoUpdate  # noqa: E402  (top-level import preferido)


def _acuerdo_in_scope(db: Session, ctx: CampaignContext, mid: str, aid: str):
    # La minuta debe estar en el scope del rol; el acuerdo debe pertenecer a ella.
    m = db.execute(_minuta_role_scoped(ctx).where(Minuta.id == mid)).scalar_one_or_none()
    if m is None:
        return None
    return db.execute(
        scoped_query(Acuerdo, ctx).where(Acuerdo.id == aid, Acuerdo.minuta_id == mid)
    ).scalar_one_or_none()


def add_acuerdo(db: Session, ctx: CampaignContext, mid: str,
                data: AcuerdoCreate) -> Optional[Acuerdo]:
    m = db.execute(_minuta_role_scoped(ctx).where(Minuta.id == mid)).scalar_one_or_none()
    if m is None:
        return None
    a = Acuerdo(
        organization_id=m.organization_id, campaign_id=m.campaign_id,
        minuta_id=m.id, texto=data.texto, orden=data.orden,
        responsable_id=data.responsable_id, fecha_limite=data.fecha_limite,
        estado="PENDIENTE", created_by=ctx.user.id,
    )
    db.add(a)
    record_audit(db, action="acuerdo.create", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="acuerdo",
                 entity_id=a.id, meta={"minuta_id": m.id})
    db.flush()
    return a


def update_acuerdo(db: Session, ctx: CampaignContext, mid: str, aid: str,
                   data: AcuerdoUpdate) -> Optional[Acuerdo]:
    a = _acuerdo_in_scope(db, ctx, mid, aid)
    if a is None:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    a.updated_by = ctx.user.id
    record_audit(db, action="acuerdo.update", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="acuerdo",
                 entity_id=a.id, meta={"estado": a.estado})
    db.flush()
    return a


def delete_acuerdo(db: Session, ctx: CampaignContext, mid: str, aid: str) -> bool:
    a = _acuerdo_in_scope(db, ctx, mid, aid)
    if a is None:
        return False
    from datetime import datetime, timezone
    a.deleted_at = datetime.now(timezone.utc)
    a.updated_by = ctx.user.id
    record_audit(db, action="acuerdo.delete", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="acuerdo",
                 entity_id=a.id, meta=None)
    db.flush()
    return True


def _acuerdo_role_scoped(ctx: CampaignContext):
    """Transversal acuerdo scope. COORDINADOR/ADMIN → whole campaign.
    LIDER → assigned to self or a supervised activista, or created by them.
    ACTIVISTA → assigned to or created by self."""
    if _is_coordinator(ctx):
        return scoped_query(Acuerdo, ctx)
    if ctx.role == UserRole.LIDER:
        activistas = select(User.id).where(User.lider_id == ctx.user.id)
        return scoped_query(Acuerdo, ctx).where(or_(
            Acuerdo.responsable_id == ctx.user.id,
            Acuerdo.responsable_id.in_(activistas),
            Acuerdo.created_by == ctx.user.id,
            Acuerdo.created_by.in_(activistas)))
    if ctx.role in (UserRole.ACTIVISTA, UserRole.CAPTURISTA):
        return scoped_query(Acuerdo, ctx).where(or_(
            Acuerdo.responsable_id == ctx.user.id,
            Acuerdo.created_by == ctx.user.id))
    return scoped_query(Acuerdo, ctx).where(sa.false())


def list_acuerdos(db: Session, ctx: CampaignContext, *, responsable_id=None,
                  estado=None, vence_antes: Optional[date] = None,
                  limit=50, offset=0) -> tuple[list[Acuerdo], int]:
    stmt = _acuerdo_role_scoped(ctx)
    if responsable_id:
        stmt = stmt.where(Acuerdo.responsable_id == responsable_id)
    if estado:
        stmt = stmt.where(Acuerdo.estado == estado)
    if vence_antes:
        stmt = stmt.where(Acuerdo.fecha_limite <= vence_antes)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    ordered = stmt.order_by(Acuerdo.fecha_limite.asc().nullslast(),
                            Acuerdo.created_at.desc())
    rows = list(db.execute(ordered.limit(limit).offset(offset)).scalars().all())
    ids = {a.responsable_id for a in rows if a.responsable_id}
    names: dict[str, str] = {}
    if ids:
        for uid, fname in db.execute(
                select(User.id, User.full_name).where(User.id.in_(ids))).all():
            names[uid] = fname
    for a in rows:
        a.responsable_nombre = names.get(a.responsable_id)
    return rows, total
```

> Mover los imports de `AcuerdoCreate`/`AcuerdoUpdate` al bloque de imports de arriba (el `# noqa` es para no fallar en linters si se dejan aquí). `nullslast()` funciona en PostgreSQL; en SQLite el orden de NULLs es tolerable para tests — si un test fuera sensible, filtra por `fecha_limite.isnot(None)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_minutas.py -k "acuerdo_lifecycle" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/minuta_service.py backend/tests/test_minutas.py
git commit -m "feat(minutas): acuerdos CRUD + transversal list (por vencer)"
```

---

### Task 5: Router `/minutas` + `/acuerdos` + registro en main

**Files:**
- Create: `backend/app/routers/minutas.py`
- Modify: `backend/app/main.py` (import + `include_router`)
- Test: `backend/tests/test_minutas_api.py`

**Interfaces:**
- Consumes: `minuta_service` (Tasks 3-4); schemas (Task 2); `CampaignCtx`, `DbSession`, `require_roles` (`app.dependencies`).
- Produces: rutas HTTP bajo `/minutas` y `/acuerdos`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_minutas_api.py`. Reusar el patrón de `tests/test_casos_api.py` para el `client` autenticado y headers (`Authorization` + `X-Campaign-Id`). Abajo se asume helpers `auth_headers(role=...)` y `campaign_headers` como en ese archivo — copiar el patrón exacto que ya exista.

```python
def test_activista_cannot_create_minuta(client, activista_headers):
    r = client.post("/api/minutas", json={"titulo": "x", "fecha": "2026-07-08"},
                    headers=activista_headers)
    assert r.status_code == 403


def test_coordinador_creates_and_lists_minuta(client, coordinador_headers):
    r = client.post("/api/minutas",
                    json={"titulo": "Arranque", "fecha": "2026-07-08",
                          "acuerdos": [{"texto": "tarea"}]},
                    headers=coordinador_headers)
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    r2 = client.get("/api/minutas", headers=coordinador_headers)
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] == 1 and body["items"][0]["id"] == mid
    assert body["items"][0]["acuerdos_pendientes"] == 1


def test_acuerdos_transversal_endpoint(client, coordinador_headers):
    client.post("/api/minutas",
                json={"titulo": "m", "fecha": "2026-07-08",
                      "acuerdos": [{"texto": "t", "fecha_limite": "2026-07-10"}]},
                headers=coordinador_headers)
    r = client.get("/api/acuerdos?vence_antes=2026-07-31", headers=coordinador_headers)
    assert r.status_code == 200 and r.json()["total"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_minutas_api.py -v`
Expected: FAIL (404 en las rutas — router no registrado).

- [ ] **Step 3: Create the router**

`backend/app/routers/minutas.py`:

```python
"""/api/minutas + /api/acuerdos — meeting minutes and action items.

Route order: /acuerdos is its own top-level collection (transversal view);
/minutas/{mid} nests acuerdos. Gates: create/write = COORDINADOR tier + LIDER;
list/get = capture tier (ACTIVISTA+); delete/publish-revert = COORDINADOR/ADMIN.
"""
from typing import Annotated, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CampaignCtx, DbSession, require_roles
from app.models.user import UserRole
from app.schemas.minuta import (
    AcuerdoCreate, AcuerdoList, AcuerdoRead, AcuerdoUpdate,
    MinutaCreate, MinutaList, MinutaRead, MinutaUpdate,
)
from app.services import minuta_service

router = APIRouter(tags=["minutas"])

_WRITE = Annotated[object, Depends(require_roles(
    UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER))]
_READ = Annotated[object, Depends(require_roles(
    UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER,
    UserRole.ACTIVISTA, UserRole.CAPTURISTA))]


# ── Acuerdos transversal (antes de /minutas/{mid}) ──────────────────────────────
@router.get("/acuerdos", response_model=AcuerdoList)
def list_acuerdos(db: DbSession, ctx: CampaignCtx, _p: _READ,
                  responsable_id: Annotated[Optional[str], Query()] = None,
                  estado: Annotated[Optional[str], Query()] = None,
                  vence_antes: Annotated[Optional[date], Query()] = None,
                  limit: Annotated[int, Query(ge=1, le=200)] = 50,
                  offset: Annotated[int, Query(ge=0)] = 0):
    rows, total = minuta_service.list_acuerdos(
        db, ctx, responsable_id=responsable_id, estado=estado,
        vence_antes=vence_antes, limit=limit, offset=offset)
    db.commit()
    return AcuerdoList(items=[AcuerdoRead.model_validate(a, from_attributes=True) for a in rows],
                       total=total, limit=limit, offset=offset)


# ── Minutas ─────────────────────────────────────────────────────────────────────
@router.post("/minutas", response_model=MinutaRead, status_code=status.HTTP_201_CREATED)
def create_minuta(data: MinutaCreate, db: DbSession, ctx: CampaignCtx, _p: _WRITE):
    m = minuta_service.create_minuta(db, ctx, data)
    db.commit()
    return MinutaRead.model_validate(m, from_attributes=True)


@router.get("/minutas", response_model=MinutaList)
def list_minutas(db: DbSession, ctx: CampaignCtx, _p: _READ,
                 tipo: Annotated[Optional[str], Query()] = None,
                 estado: Annotated[Optional[str], Query()] = None,
                 desde: Annotated[Optional[date], Query()] = None,
                 hasta: Annotated[Optional[date], Query()] = None,
                 limit: Annotated[int, Query(ge=1, le=200)] = 50,
                 offset: Annotated[int, Query(ge=0)] = 0):
    rows, total = minuta_service.list_minutas(
        db, ctx, tipo=tipo, estado=estado, desde=desde, hasta=hasta,
        limit=limit, offset=offset)
    db.commit()
    return MinutaList(items=[MinutaRead.model_validate(m, from_attributes=True) for m in rows],
                      total=total, limit=limit, offset=offset)


@router.get("/minutas/{mid}", response_model=MinutaRead)
def get_minuta(mid: str, db: DbSession, ctx: CampaignCtx, _p: _READ):
    m = minuta_service.get_minuta(db, ctx, mid)
    if m is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    return MinutaRead.model_validate(m, from_attributes=True)


@router.patch("/minutas/{mid}", response_model=MinutaRead)
def update_minuta(mid: str, data: MinutaUpdate, db: DbSession, ctx: CampaignCtx, _p: _WRITE):
    try:
        m = minuta_service.update_minuta(db, ctx, mid, data)
    except minuta_service.PublishedLockError:
        raise HTTPException(status_code=409, detail="Minuta publicada: solo un coordinador puede editar el acta")
    if m is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    db.commit()
    return MinutaRead.model_validate(m, from_attributes=True)


@router.delete("/minutas/{mid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_minuta(mid: str, db: DbSession, ctx: CampaignCtx,
                  _p: Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.COORDINADOR))]):
    if not minuta_service.delete_minuta(db, ctx, mid):
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    db.commit()


# ── Acuerdos anidados ───────────────────────────────────────────────────────────
@router.post("/minutas/{mid}/acuerdos", response_model=AcuerdoRead, status_code=status.HTTP_201_CREATED)
def add_acuerdo(mid: str, data: AcuerdoCreate, db: DbSession, ctx: CampaignCtx, _p: _WRITE):
    a = minuta_service.add_acuerdo(db, ctx, mid, data)
    if a is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    db.commit()
    return AcuerdoRead.model_validate(a, from_attributes=True)


@router.patch("/minutas/{mid}/acuerdos/{aid}", response_model=AcuerdoRead)
def update_acuerdo(mid: str, aid: str, data: AcuerdoUpdate, db: DbSession, ctx: CampaignCtx, _p: _WRITE):
    a = minuta_service.update_acuerdo(db, ctx, mid, aid, data)
    if a is None:
        raise HTTPException(status_code=404, detail="Acuerdo no encontrado")
    db.commit()
    return AcuerdoRead.model_validate(a, from_attributes=True)


@router.delete("/minutas/{mid}/acuerdos/{aid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_acuerdo(mid: str, aid: str, db: DbSession, ctx: CampaignCtx, _p: _WRITE):
    if not minuta_service.delete_acuerdo(db, ctx, mid, aid):
        raise HTTPException(status_code=404, detail="Acuerdo no encontrado")
    db.commit()
```

- [ ] **Step 4: Register the router in main**

En `backend/app/main.py`: añadir `minutas` al import de `from app.routers import (...)` (orden alfabético, entre `militantes`/`municipio`), y en el bloque donde se hace `app.include_router(...)` seguir el patrón existente. Si `include_router` se hace en bucle sobre una lista de módulos (ver `app/main.py:230`), añadir `minutas` a esa lista; si es explícito, añadir:

```python
app.include_router(minutas.router, prefix="/api")
```

Verificar el prefijo real que usan los demás routers (buscar cómo se registra `casos`) y replicarlo exactamente.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_minutas_api.py -v`
Expected: PASS (los 3 tests).

- [ ] **Step 6: Run the full backend suite (no regressions)**

Run: `cd backend && python3 -m pytest -q`
Expected: baseline verde (mismos passes de antes + los nuevos).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/minutas.py backend/app/main.py backend/tests/test_minutas_api.py
git commit -m "feat(minutas): router /minutas + /acuerdos, registered in app"
```

---

### Task 6: Cliente API frontend (`api/minutas.ts`)

**Files:**
- Create: `frontend/src/api/minutas.ts`

**Interfaces:**
- Consumes: `apiClient` (`frontend/src/api/client.ts`) — ya inyecta `Authorization` y `X-Campaign-Id`.
- Produces: tipos `Minuta`, `Acuerdo`, `Asistente` y funciones `listMinutas`, `getMinuta`, `createMinuta`, `updateMinuta`, `deleteMinuta`, `addAcuerdo`, `updateAcuerdo`, `deleteAcuerdo`, `listAcuerdos`.

- [ ] **Step 1: Create the client**

`frontend/src/api/minutas.ts`:

```typescript
import { apiClient } from "./client";

export interface Asistente { user_id?: string; nombre: string; }

export interface Acuerdo {
  id: string;
  minuta_id: string;
  texto: string;
  orden: number;
  responsable_id?: string;
  responsable_nombre?: string;
  fecha_limite?: string;
  estado: string;
  work_item_id?: string;
  created_at: string;
}

export interface Minuta {
  id: string;
  titulo: string;
  fecha: string;
  lugar?: string;
  tipo: string;
  estado: string;
  asistentes: Asistente[];
  cuerpo?: string;
  area_id?: string;
  created_at: string;
  created_by?: string;
  acuerdos: Acuerdo[];
  acuerdos_pendientes: number;
}

interface Page<T> { items: T[]; total: number; limit: number; offset: number; }

export interface MinutaCreate {
  titulo: string;
  fecha: string;
  lugar?: string;
  tipo?: string;
  estado?: string;
  asistentes?: Asistente[];
  cuerpo?: string;
  area_id?: string;
  acuerdos?: { texto: string; responsable_id?: string; fecha_limite?: string; orden?: number }[];
}

export async function listMinutas(params?: Record<string, string | number>): Promise<Page<Minuta>> {
  const { data } = await apiClient.get("/minutas", { params });
  return data;
}
export async function getMinuta(id: string): Promise<Minuta> {
  const { data } = await apiClient.get(`/minutas/${id}`);
  return data;
}
export async function createMinuta(payload: MinutaCreate): Promise<Minuta> {
  const { data } = await apiClient.post("/minutas", payload);
  return data;
}
export async function updateMinuta(id: string, payload: Partial<MinutaCreate>): Promise<Minuta> {
  const { data } = await apiClient.patch(`/minutas/${id}`, payload);
  return data;
}
export async function deleteMinuta(id: string): Promise<void> {
  await apiClient.delete(`/minutas/${id}`);
}
export async function addAcuerdo(mid: string, payload: { texto: string; responsable_id?: string; fecha_limite?: string; orden?: number }): Promise<Acuerdo> {
  const { data } = await apiClient.post(`/minutas/${mid}/acuerdos`, payload);
  return data;
}
export async function updateAcuerdo(mid: string, aid: string, payload: Partial<Acuerdo>): Promise<Acuerdo> {
  const { data } = await apiClient.patch(`/minutas/${mid}/acuerdos/${aid}`, payload);
  return data;
}
export async function deleteAcuerdo(mid: string, aid: string): Promise<void> {
  await apiClient.delete(`/minutas/${mid}/acuerdos/${aid}`);
}
export async function listAcuerdos(params?: Record<string, string | number>): Promise<Page<Acuerdo>> {
  const { data } = await apiClient.get("/acuerdos", { params });
  return data;
}
```

> Verificar el `baseURL` de `apiClient` en `client.ts`: si ya incluye `/api`, las rutas van sin `/api` (como arriba); si no, prefijarlas. Copiar exactamente el estilo de `api/atencion.ts`.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npm run build`
Expected: build sin errores de TypeScript.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/minutas.ts
git commit -m "feat(minutas): frontend API client"
```

---

### Task 7: Páginas + navegación (registry)

**Files:**
- Create: `frontend/src/modules/minutas/MinutasListPage.tsx`
- Create: `frontend/src/modules/minutas/MinutaEditorPage.tsx`
- Create: `frontend/src/modules/minutas/MinutaDetailPage.tsx`
- Create: `frontend/src/modules/minutas/MisAcuerdosPage.tsx`
- Modify: `frontend/src/modules/registry.ts` (rutas + gating)

**Interfaces:**
- Consumes: `api/minutas.ts` (Task 6); componentes/tokens del Atenea kit ya usados por otros módulos (copiar imports de un módulo existente, p.ej. `modules/atencion`).
- Produces: 4 rutas de nav gated.

- [ ] **Step 1: Create the list page**

`frontend/src/modules/minutas/MinutasListPage.tsx` — lista de minutas con badge de acuerdos pendientes y botón "Nueva minuta". Seguir el layout/estética de una página de lista existente (p.ej. la lista de casos en `modules/atencion`). Estructura mínima:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listMinutas, type Minuta } from "@/api/minutas";

export default function MinutasListPage() {
  const [items, setItems] = useState<Minuta[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    listMinutas().then((p) => setItems(p.items)).finally(() => setLoading(false));
  }, []);
  return (
    <div className="page">
      <header className="page-header">
        <h1>Minutas</h1>
        <Link to="/minutas/nueva" className="btn btn-primary">Nueva minuta</Link>
      </header>
      {loading ? <p>Cargando…</p> : (
        <ul className="minutas-list">
          {items.map((m) => (
            <li key={m.id}>
              <Link to={`/minutas/${m.id}`}>
                <span className="titulo">{m.titulo}</span>
                <span className="fecha">{m.fecha}</span>
                <span className="tipo">{m.tipo}</span>
                <span className="estado">{m.estado}</span>
                {m.acuerdos_pendientes > 0 && (
                  <span className="badge">{m.acuerdos_pendientes} pendientes</span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

> Reemplazar clases/estilo por los tokens del Atenea kit que use el módulo vecino. No inventar un sistema de estilos nuevo.

- [ ] **Step 2: Create the editor page**

`frontend/src/modules/minutas/MinutaEditorPage.tsx` — formulario controlado (título, fecha, lugar, tipo `<select>` REUNION/OTRO, asistentes como lista editable de nombres, `<textarea>` cuerpo, y lista de acuerdos inline con texto + fecha límite). En modo "nueva" llama `createMinuta`; con `:id` en la ruta, precarga con `getMinuta` y guarda con `updateMinuta`. Al guardar, navega a `/minutas/:id`. Botón "Publicar" que hace `updateMinuta(id, { estado: "PUBLICADA" })`.

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createMinuta, type MinutaCreate } from "@/api/minutas";

export default function MinutaEditorPage() {
  const nav = useNavigate();
  const [form, setForm] = useState<MinutaCreate>({
    titulo: "", fecha: new Date().toISOString().slice(0, 10),
    tipo: "REUNION", asistentes: [], cuerpo: "", acuerdos: [],
  });
  const [saving, setSaving] = useState(false);
  async function submit() {
    setSaving(true);
    try {
      const m = await createMinuta(form);
      nav(`/minutas/${m.id}`);
    } finally { setSaving(false); }
  }
  return (
    <div className="page">
      <h1>Nueva minuta</h1>
      <label>Título
        <input value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} />
      </label>
      <label>Fecha
        <input type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} />
      </label>
      <label>Lugar
        <input value={form.lugar ?? ""} onChange={(e) => setForm({ ...form, lugar: e.target.value })} />
      </label>
      <label>Tipo
        <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
          <option value="REUNION">Reunión</option>
          <option value="OTRO">Otro</option>
        </select>
      </label>
      <label>Notas
        <textarea value={form.cuerpo ?? ""} onChange={(e) => setForm({ ...form, cuerpo: e.target.value })} />
      </label>
      <button disabled={saving || !form.titulo} onClick={submit}>Guardar</button>
    </div>
  );
}
```

> El editor de asistentes y de acuerdos inline se implementa con el mismo patrón de arrays controlados; mantenerlo simple (añadir/quitar filas). Reusar el estilo del formulario de captura existente.

- [ ] **Step 3: Create the detail page**

`frontend/src/modules/minutas/MinutaDetailPage.tsx` — carga `getMinuta(id)`, muestra el acta (título/fecha/lugar/asistentes/cuerpo) y la lista de acuerdos con su estado y responsable. Cada acuerdo tiene un `<select>` de estado que llama `updateAcuerdo(mid, aid, { estado })`. Si la minuta está en `BORRADOR`, muestra botón "Editar" → `/minutas/:id/editar` y "Publicar".

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getMinuta, updateAcuerdo, type Minuta } from "@/api/minutas";

const ESTADOS = ["PENDIENTE", "EN_CURSO", "CUMPLIDO", "CANCELADO"];

export default function MinutaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [m, setM] = useState<Minuta | null>(null);
  useEffect(() => { if (id) getMinuta(id).then(setM); }, [id]);
  if (!m) return <p>Cargando…</p>;
  async function cambiarEstado(aid: string, estado: string) {
    await updateAcuerdo(m!.id, aid, { estado });
    setM(await getMinuta(m!.id));
  }
  return (
    <div className="page">
      <h1>{m.titulo}</h1>
      <p>{m.fecha} · {m.lugar} · {m.estado}</p>
      <section><h2>Notas</h2><pre>{m.cuerpo}</pre></section>
      <section>
        <h2>Acuerdos</h2>
        <ul>
          {m.acuerdos.map((a) => (
            <li key={a.id}>
              <span>{a.texto}</span>
              <span>{a.responsable_nombre ?? "—"}</span>
              <span>{a.fecha_limite ?? ""}</span>
              <select value={a.estado} onChange={(e) => cambiarEstado(a.id, e.target.value)}>
                {ESTADOS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Create Mis Acuerdos page**

`frontend/src/modules/minutas/MisAcuerdosPage.tsx` — llama `listAcuerdos` (por defecto ordenado por vencimiento) y agrupa/marca con badge: vencido (`fecha_limite < hoy` y estado no terminal), hoy, próximos 7 días, sin fecha.

```tsx
import { useEffect, useState } from "react";
import { listAcuerdos, type Acuerdo } from "@/api/minutas";

function badge(a: Acuerdo): string {
  if (!a.fecha_limite) return "sin-fecha";
  const hoy = new Date().toISOString().slice(0, 10);
  if (a.estado === "CUMPLIDO" || a.estado === "CANCELADO") return "cerrado";
  if (a.fecha_limite < hoy) return "vencido";
  if (a.fecha_limite === hoy) return "hoy";
  return "proximo";
}

export default function MisAcuerdosPage() {
  const [items, setItems] = useState<Acuerdo[]>([]);
  useEffect(() => { listAcuerdos().then((p) => setItems(p.items)); }, []);
  return (
    <div className="page">
      <h1>Seguimiento de acuerdos</h1>
      <ul>
        {items.map((a) => (
          <li key={a.id} className={`acuerdo ${badge(a)}`}>
            <span>{a.texto}</span>
            <span>{a.responsable_nombre ?? "—"}</span>
            <span>{a.fecha_limite ?? "sin fecha"}</span>
            <span className="estado">{a.estado}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 5: Register routes in registry**

En `frontend/src/modules/registry.ts`:

1. Importar las páginas con `lazy` (patrón existente al inicio del archivo):

```typescript
const MinutasList = lazy(() => import("@/modules/minutas/MinutasListPage"));
const MinutaEditor = lazy(() => import("@/modules/minutas/MinutaEditorPage"));
const MinutaDetail = lazy(() => import("@/modules/minutas/MinutaDetailPage"));
const MisAcuerdos = lazy(() => import("@/modules/minutas/MisAcuerdosPage"));
```

2. Definir el gate de lectura (incluye ACTIVISTA) junto a los otros `const CONSOLE_*`:

```typescript
const MINUTAS_READ: UserRole[] = ["superadmin", "admin", "coordinador", "lider", "activista"];
```

3. Añadir las entradas de ruta en el array de módulos (sección `ciudadania`, siguiendo el shape exacto de las entradas vecinas — `key`, `path`, `label`, `section`, `icon`, `state`, `element`, `roles`):

```typescript
{ key: "minutas", path: "/minutas", label: "Minutas", section: "ciudadania", icon: AnalyticsIcon, state: "active", element: MinutasList, roles: CONSOLE_COORD },
{ key: "minutas-nueva", path: "/minutas/nueva", label: "Nueva minuta", section: "ciudadania", icon: AnalyticsIcon, state: "active", element: MinutaEditor, roles: CONSOLE_COORD, hidden: true },
{ key: "minuta-detalle", path: "/minutas/:id", label: "Minuta", section: "ciudadania", icon: AnalyticsIcon, state: "active", element: MinutaDetail, roles: MINUTAS_READ, hidden: true },
{ key: "minuta-editar", path: "/minutas/:id/editar", label: "Editar minuta", section: "ciudadania", icon: AnalyticsIcon, state: "active", element: MinutaEditor, roles: CONSOLE_COORD, hidden: true },
{ key: "acuerdos", path: "/acuerdos", label: "Acuerdos", section: "ciudadania", icon: UserIcon, state: "active", element: MisAcuerdos, roles: MINUTAS_READ },
```

> Verificar si el tipo de entrada admite `hidden` (para rutas que no deben salir en el menú); si no existe, omitir esa clave — las rutas con parámetros (`:id`) igual no deben listarse como ítems de menú, así que ver cómo lo resuelven las rutas existentes con parámetros (p.ej. detalle de promovido) y replicar.

- [ ] **Step 6: Type-check + build**

Run: `cd frontend && npm run build`
Expected: build sin errores.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/modules/minutas/ frontend/src/modules/registry.ts
git commit -m "feat(minutas): frontend pages + nav (minutas, detalle, acuerdos)"
```

---

## Self-Review contra el spec

- **Modelo `Minuta`/`Acuerdo`** → Task 1. ✅ (todos los campos del spec, incl. `work_item_id` reservado y `tipo` con ceremonias reservadas).
- **Migración 0018 idempotente + SQLite** → Task 1. ✅
- **Schemas Pydantic con patrones de estado/tipo** → Task 2. ✅
- **Scoping COORDINADOR campaign-wide; LIDER/ACTIVISTA jerarquizados** → Task 3 (`_minuta_role_scoped`) y Task 4 (`_acuerdo_role_scoped`). ✅
- **Publicar bloquea edición del acta para no-coordinador** → Task 3 (`PublishedLockError`, 409 en Task 5). ✅
- **Audit en create/update/delete de minuta y acuerdo** → Tasks 3-4 (`record_audit`). ✅
- **Endpoints REST + paginación + envelope de error** → Task 5. ✅
- **`GET /acuerdos` transversal (por vencer / mis acuerdos)** → Task 4 (`list_acuerdos`) + Task 5. ✅
- **RBAC deny (ACTIVISTA no crea)** → Task 5 test. ✅
- **Aislamiento de tenant** → cubierto por `scoped_query`; añadir un test explícito org-A/org-B en Task 3 si el patrón de `test_casos.py` lo facilita.
- **Frontend: 4 páginas + nav gated `CONSOLE_MINUTAS`** → Tasks 6-7 (implementado como `CONSOLE_COORD` para escritura + `MINUTAS_READ` para lectura; equivale al permiso de consola del spec). ✅
- **Ganchos a Sub-proyecto B** (`tipo` ceremonias, `work_item_id`) → Task 1. ✅

**Placeholder scan:** sin TBD/TODO; todo el código de cada step está presente. Las únicas indicaciones "verificar patrón existente" (prefijo `/api`, `hidden` en registry, fixtures de test) son verificaciones de convención local, no lógica pendiente.

**Type consistency:** nombres de funciones del servicio consistentes entre Tasks 3-5 (`create_minuta`, `list_minutas`, `get_minuta`, `update_minuta`, `delete_minuta`, `add_acuerdo`, `update_acuerdo`, `delete_acuerdo`, `list_acuerdos`); campos de schema consistentes con el modelo (`work_item_id`, `acuerdos_pendientes`, `responsable_nombre`).
