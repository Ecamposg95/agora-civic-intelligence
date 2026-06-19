# SP0a — Platform Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the multi-tenant, multi-campaign spine — Campaign→Contest container, territory hierarchy to sección/casilla (shared-global cartography), app-layer `(tenant_id, campaign_id)` scoping, Alembic migrations, and a campaign switcher — so SP1 and SP2 can start.

**Architecture:** Additive on the existing FastAPI/SQLAlchemy-2.0 backend. New models compose the existing `UUIDMixin/TenantMixin/AuditMixin`; a new `CampaignMixin` adds `campaign_id`. A `scoped_query` chokepoint + an extended request context enforce isolation. Alembic replaces `create_all` for Postgres; the SQLite test suite keeps `create_all`. Frontend adds a `campaignStore` + axios header, reusing the design system.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (`Mapped`/`mapped_column`), Alembic (new), PostGIS (Postgres) / SQLite (tests), pytest, React 18 + zustand + axios.

**Spec:** `docs/superpowers/specs/2026-06-18-sp0a-platform-spine-design.md`

---

## Conventions
- Repo root: `/mnt/c/Users/ecamp/Devs/agora-civic-intelligence`. Branch: `feat/sp0a-spine` (create from main; do NOT work on main).
- Backend cmds from `backend/`. Run tests: `cd backend && python3 -m pytest -q` (or a specific `path::test`).
- Frontend build: `cd frontend && rm -rf dist && find . -maxdepth 1 -name '*.tsbuildinfo' -delete; npm run lint && npm run build`.
- Commit from repo root via `git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence ...`. Trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Do NOT push (deploy is the user's call at the end). Each task: failing test → confirm fail → implement → confirm pass → commit.
- **Golden rule:** tenant/campaign come from auth/context, never request body.

## File Structure
**Create:** `backend/app/models/catalog.py`, `backend/app/models/campaign.py`, `backend/app/core/scoping.py`, `backend/app/schemas/campaign.py`, `backend/app/schemas/catalog.py`, `backend/app/services/campaign_service.py`, `backend/app/routers/campaigns.py`, `backend/app/routers/catalogs.py`, `backend/app/routers/territory.py`, `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/0001_baseline.py`, `backend/migrations/versions/0002_sp0a_spine.py`, `backend/scripts/seed_catalogs.py`, `backend/tests/test_campaigns.py`, `backend/tests/test_scoping.py`, `backend/tests/test_territory_hierarchy.py`, `frontend/src/store/campaignStore.ts`, `frontend/src/components/layout/CampaignSwitcher.tsx`, `frontend/src/modules/campaigns/CampaignsPage.tsx`.
**Modify:** `backend/app/models/base.py` (+`CampaignMixin`), `backend/app/models/electoral_area.py` (hierarchy + nullable org), `backend/app/dependencies.py` (+campaign context), `backend/app/bootstrap.py` (Alembic on Postgres), `backend/app/main.py` (register routers), `backend/tests/conftest.py` (new tables + campaign seed), `frontend/src/api/client.ts` (X-Campaign-Id interceptor), `frontend/src/components/layout/Topbar.tsx` (mount switcher), `frontend/src/modules/registry.ts` (Campaigns admin route).

---

### Task 1: Catalog models (Cargo, Party, Coalition)

**Files:** Create `backend/app/models/catalog.py`; Modify `backend/app/models/__init__.py`; Test `backend/tests/test_campaigns.py`.

- [ ] **Step 1: Failing test** — append to a new `backend/tests/test_campaigns.py`:
```python
from app.models.catalog import Cargo, Party, Coalition, CoalitionParty


def test_catalog_models_exist_and_are_global():
    # Catalogs are platform reference data: no tenant column.
    assert not hasattr(Cargo, "organization_id")
    assert {c.name for c in Cargo.__table__.columns} >= {"id", "key", "label", "ambito", "territory_level"}
    assert {c.name for c in Party.__table__.columns} >= {"id", "key", "name", "short", "color"}
    assert {c.name for c in Coalition.__table__.columns} >= {"id", "key", "name", "color"}
    assert {c.name for c in CoalitionParty.__table__.columns} >= {"coalition_id", "party_id"}
```
- [ ] **Step 2: Run → FAIL** `cd backend && python3 -m pytest tests/test_campaigns.py::test_catalog_models_exist_and_are_global -q` → ModuleNotFoundError.
- [ ] **Step 3: Implement** `backend/app/models/catalog.py`:
```python
"""Platform-global reference catalogs (no tenant scoping)."""
from __future__ import annotations

import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class Ambito(str, enum.Enum):
    FEDERAL = "federal"
    ESTATAL = "estatal"
    MUNICIPAL = "municipal"


class Cargo(UUIDMixin, Base):
    """A contested office (gubernatura, diputación federal, etc.)."""
    __tablename__ = "cargos"
    key: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    ambito: Mapped[Ambito] = mapped_column(Enum(Ambito, name="cargo_ambito"), nullable=False)
    # AreaLevel value (string) the office maps to, e.g. "estado","distrito_local".
    territory_level: Mapped[str] = mapped_column(String(40), nullable=False)


class Party(UUIDMixin, Base):
    __tablename__ = "parties"
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    short: Mapped[str] = mapped_column(String(40), nullable=False)
    color: Mapped[str] = mapped_column(String(9), nullable=False, default="#8ba0a8")


class Coalition(UUIDMixin, Base):
    __tablename__ = "coalitions"
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    color: Mapped[str] = mapped_column(String(9), nullable=False, default="#8ba0a8")


class CoalitionParty(UUIDMixin, Base):
    __tablename__ = "coalition_parties"
    coalition_id: Mapped[str] = mapped_column(ForeignKey("coalitions.id", ondelete="CASCADE"), index=True, nullable=False)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id", ondelete="CASCADE"), index=True, nullable=False)
```
Then add to `backend/app/models/__init__.py` the import (so it registers on `Base.metadata` for bootstrap): `from app.models.catalog import Cargo, Party, Coalition, CoalitionParty  # noqa: F401`.
- [ ] **Step 4: Register tables in tests** — in `backend/tests/conftest.py`, import the new models and add their `__table__` to the `Base.metadata.create_all(engine, tables=[...])` list: add `Cargo.__table__, Party.__table__, Coalition.__table__, CoalitionParty.__table__`. (Import: `from app.models.catalog import Cargo, Party, Coalition, CoalitionParty`.)
- [ ] **Step 5: Run → PASS** the same pytest command.
- [ ] **Step 6: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add backend/app/models/catalog.py backend/app/models/__init__.py backend/tests/conftest.py backend/tests/test_campaigns.py
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): global catalog models (cargo/party/coalition)"
```

---

### Task 2: Campaign, Contest, CampaignMembership models + CampaignMixin

**Files:** Modify `backend/app/models/base.py`, `backend/app/models/__init__.py`, `backend/tests/conftest.py`; Create `backend/app/models/campaign.py`; Test `backend/tests/test_campaigns.py`.

- [ ] **Step 1: Failing test** — append to `backend/tests/test_campaigns.py`:
```python
from app.models.campaign import Campaign, Contest, CampaignMembership, CampaignStatus
from app.models.base import CampaignMixin


def test_campaign_contest_membership_shape():
    assert {c.name for c in Campaign.__table__.columns} >= {"id", "organization_id", "name", "cycle", "status"}
    assert {c.name for c in Contest.__table__.columns} >= {"id", "organization_id", "campaign_id", "cargo_id", "territory_id", "election_date"}
    assert {c.name for c in CampaignMembership.__table__.columns} >= {"id", "user_id", "campaign_id", "role"}
    # CampaignMixin contributes a NOT NULL campaign_id FK.
    col = CampaignMixin.__dict__["campaign_id"]
    assert col is not None
    assert CampaignStatus.DRAFT.value == "draft"
```
- [ ] **Step 2: Run → FAIL** `python3 -m pytest tests/test_campaigns.py::test_campaign_contest_membership_shape -q`.
- [ ] **Step 3: Implement** — add to `backend/app/models/base.py` (after `TenantMixin`):
```python
class CampaignMixin:
    """Campaign scoping for operational/contest-bound entities."""
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
```
Create `backend/app/models/campaign.py`:
```python
"""Campaign container (multi-contest) + membership, tenant-scoped."""
from __future__ import annotations

import enum
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import AuditMixin, CampaignMixin, TenantMixin, UUIDMixin
from app.models.user import UserRole


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class LicenseTier(str, enum.Enum):
    STANDARD = "standard"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Campaign(UUIDMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "campaigns"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"), default=CampaignStatus.DRAFT, nullable=False
    )
    license_tier: Mapped[LicenseTier] = mapped_column(
        Enum(LicenseTier, name="license_tier"), default=LicenseTier.STANDARD, nullable=False
    )


class Contest(UUIDMixin, TenantMixin, AuditMixin, CampaignMixin, Base):
    __tablename__ = "contests"
    cargo_id: Mapped[str] = mapped_column(ForeignKey("cargos.id"), index=True, nullable=False)
    # The territory where the office is contested (FK electoral_areas).
    territory_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("electoral_areas.id"), index=True, nullable=True
    )
    election_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class CampaignMembership(UUIDMixin, AuditMixin, Base):
    __tablename__ = "campaign_memberships"
    __table_args__ = (UniqueConstraint("user_id", "campaign_id", name="uq_campaign_member"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.VIEWER, nullable=False)
```
NOTE: `Contest` composes `CampaignMixin` which references `campaigns.id` — declare `Campaign` first (same module, fine). Add to `backend/app/models/__init__.py`: `from app.models.campaign import Campaign, Contest, CampaignMembership  # noqa: F401`.
- [ ] **Step 4: Register in conftest** — import `Campaign, Contest, CampaignMembership` and add their `__table__`s to the create_all list (order: after Cargo, after users/areas exist — SQLite create_all resolves FKs regardless of order). Add `Campaign.__table__, Contest.__table__, CampaignMembership.__table__`.
- [ ] **Step 5: Run → PASS**.
- [ ] **Step 6: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add backend/app/models/base.py backend/app/models/campaign.py backend/app/models/__init__.py backend/tests/conftest.py backend/tests/test_campaigns.py
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): Campaign/Contest/CampaignMembership models + CampaignMixin"
```

---

### Task 3: Territory hierarchy on ElectoralArea (levels, parent, redundant FKs, nullable tenant)

**Files:** Modify `backend/app/models/electoral_area.py`; Test `backend/tests/test_territory_hierarchy.py`.

- [ ] **Step 1: Failing test** — create `backend/tests/test_territory_hierarchy.py`:
```python
from app.models.electoral_area import AreaLevel, ElectoralArea
from tests.conftest import TestingSessionLocal


def test_arealevel_has_electoral_levels():
    vals = {l.value for l in AreaLevel}
    assert {"estado", "municipio", "distrito_federal", "distrito_local", "seccion", "casilla"} <= vals


def test_seccion_redundant_fks_and_nullable_tenant():
    cols = {c.name for c in ElectoralArea.__table__.columns}
    assert {"parent_id", "estado_id", "municipio_id", "distrito_federal_id", "distrito_local_id", "seccion_id"} <= cols
    assert ElectoralArea.__table__.c.organization_id.nullable is True


def test_global_reference_area_has_null_tenant():
    db = TestingSessionLocal()
    try:
        estado = ElectoralArea(name="México", level=AreaLevel.ESTADO, organization_id=None)
        db.add(estado); db.flush()
        seccion = ElectoralArea(name="0001", level=AreaLevel.SECCION, organization_id=None, estado_id=estado.id, parent_id=estado.id)
        db.add(seccion); db.flush()
        assert seccion.estado_id == estado.id
        db.rollback()
    finally:
        db.close()
```
- [ ] **Step 2: Run → FAIL** `python3 -m pytest tests/test_territory_hierarchy.py -q`.
- [ ] **Step 3: Implement** — edit `backend/app/models/electoral_area.py`:
  (a) Extend `AreaLevel` (keep existing members; add):
```python
    NATION = "nation"
    ESTADO = "estado"
    MUNICIPIO = "municipio"
    DISTRITO_FEDERAL = "distrito_federal"
    DISTRITO_LOCAL = "distrito_local"
    SECCION = "seccion"
    COLONIA = "colonia"
    MANZANA = "manzana"
    CASILLA = "casilla"
```
  (b) STOP composing `TenantMixin` on `ElectoralArea` (so tenant can be nullable for global reference). Replace the class line `class ElectoralArea(UUIDMixin, TenantMixin, AuditMixin, Base):` with `class ElectoralArea(UUIDMixin, AuditMixin, Base):` and add an explicit nullable `organization_id` + the hierarchy columns:
```python
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=True
    )  # NULL = shared global reference cartography
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("electoral_areas.id", ondelete="SET NULL"), index=True, nullable=True
    )
    estado_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("electoral_areas.id"), index=True, nullable=True)
    municipio_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("electoral_areas.id"), index=True, nullable=True)
    distrito_federal_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("electoral_areas.id"), index=True, nullable=True)
    distrito_local_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("electoral_areas.id"), index=True, nullable=True)
    seccion_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("electoral_areas.id"), index=True, nullable=True)
```
  Keep `name`, `code`, `level`, `geometry`. Keep the `organization` relationship but make it match the nullable FK (relationship still valid). The multiple self-FKs all target `electoral_areas.id` — SQLAlchemy needs explicit `foreign_keys` on any self-relationship; we use plain columns (no ORM `parent`/`children` relationship in SP0a to avoid ambiguity — query by columns). If you add a `parent` relationship, set `remote_side=[id]` and `foreign_keys=[parent_id]`.
- [ ] **Step 4: Run → PASS** (conftest already creates `ElectoralArea.__table__`).
- [ ] **Step 5: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add backend/app/models/electoral_area.py backend/tests/test_territory_hierarchy.py
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): territory hierarchy — levels, parent_id, redundant FKs, nullable tenant (global reference)"
```

---

### Task 4: Campaign request context + `scoped_query` chokepoint

**Files:** Create `backend/app/core/scoping.py`; Modify `backend/app/dependencies.py`; Test `backend/tests/test_scoping.py`.

- [ ] **Step 1: Failing test** — create `backend/tests/test_scoping.py`:
```python
from app.core.scoping import scoped_query
from app.models.campaign import Contest
from app.models.electoral_area import ElectoralArea


class _Ctx:
    def __init__(self, tenant, campaign, is_super=False):
        self.organization_id = tenant
        self.campaign_id = campaign
        self.is_superadmin = is_super


def test_scoped_query_filters_tenant_and_campaign():
    sql = str(scoped_query(Contest, _Ctx("org1", "camp1")))
    assert "organization_id" in sql and "campaign_id" in sql


def test_scoped_query_reference_model_unions_global_and_tenant():
    # ElectoralArea has no campaign_id and a nullable tenant: reference-aware.
    sql = str(scoped_query(ElectoralArea, _Ctx("org1", "camp1")))
    assert "organization_id" in sql  # filter present; allows NULL OR tenant
```
- [ ] **Step 2: Run → FAIL**.
- [ ] **Step 3: Implement** `backend/app/core/scoping.py`:
```python
"""Central tenant/campaign scoping chokepoint. All campaign-scoped reads/writes
go through scoped_query so isolation is enforced in exactly one place."""
from __future__ import annotations

from sqlalchemy import or_, select


def scoped_query(model, ctx):
    """Return a SELECT for `model` filtered by the request's tenant/campaign.

    - Soft-deleted rows excluded when the model has `deleted_at`.
    - Campaign-scoped models (have `campaign_id`) filtered by ctx.campaign_id.
    - Reference models with a NULLABLE organization_id (e.g. territory) match
      global rows (NULL) OR the tenant's own rows.
    - Tenant-scoped models filter strictly by ctx.organization_id (superadmin
      may pass a tenant explicitly; no cross-tenant read here).
    """
    stmt = select(model)
    cols = model.__table__.c

    if "deleted_at" in cols:
        stmt = stmt.where(cols.deleted_at.is_(None))

    if "organization_id" in cols:
        if cols.organization_id.nullable:
            stmt = stmt.where(or_(cols.organization_id.is_(None), cols.organization_id == ctx.organization_id))
        else:
            stmt = stmt.where(cols.organization_id == ctx.organization_id)

    if "campaign_id" in cols:
        stmt = stmt.where(cols.campaign_id == ctx.campaign_id)

    return stmt
```
Extend `backend/app/dependencies.py` — add a campaign context dependency that resolves `X-Campaign-Id` and validates membership:
```python
from fastapi import Header
from app.models.campaign import Campaign, CampaignMembership


@dataclass(frozen=True)
class CampaignContext(TenantContext):
    campaign_id: str = ""


def get_campaign_context(
    db: DbSession,
    ctx: Tenant,
    x_campaign_id: Annotated[Optional[str], Header(alias="X-Campaign-Id")] = None,
) -> CampaignContext:
    if not x_campaign_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Campaign-Id header required")
    campaign = db.execute(
        select(Campaign).where(Campaign.id == x_campaign_id, Campaign.deleted_at.is_(None))
    ).scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if not ctx.is_superadmin:
        if campaign.organization_id != ctx.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Campaign not in your organization")
        member = db.execute(
            select(CampaignMembership).where(
                CampaignMembership.campaign_id == x_campaign_id,
                CampaignMembership.user_id == ctx.user.id,
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this campaign")
    return CampaignContext(
        user=ctx.user, organization_id=ctx.organization_id, role=ctx.role, campaign_id=x_campaign_id
    )


CampaignCtx = Annotated[CampaignContext, Depends(get_campaign_context)]
```
- [ ] **Step 4: Run → PASS**.
- [ ] **Step 5: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add backend/app/core/scoping.py backend/app/dependencies.py backend/tests/test_scoping.py
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): scoped_query chokepoint + campaign request context (X-Campaign-Id)"
```

---

### Task 5: Campaign schemas + service + router (CRUD, my-campaigns) — with isolation tests

**Files:** Create `backend/app/schemas/campaign.py`, `backend/app/services/campaign_service.py`, `backend/app/routers/campaigns.py`; Modify `backend/app/main.py`, `backend/tests/conftest.py`; Test `backend/tests/test_campaigns.py`.

- [ ] **Step 1: Failing tests** — append to `backend/tests/test_campaigns.py` (uses the `client`/`auth_headers` fixtures + a campaign seeded in conftest, see Step 4):
```python
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID


def test_member_can_read_own_campaign(client):
    h = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/campaigns/mine", headers=h)
    assert r.status_code == 200
    assert any(c["id"] == ALPHA_CAMPAIGN_ID for c in r.json())


def test_non_member_tenant_cannot_use_campaign(client):
    h = auth_headers(client, "admin@beta.gov")
    r = client.get("/api/campaigns/" + ALPHA_CAMPAIGN_ID, headers={**h, "X-Campaign-Id": ALPHA_CAMPAIGN_ID})
    assert r.status_code in (403, 404)  # cross-tenant campaign is invisible


def test_missing_campaign_header_rejected(client):
    h = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/campaigns/" + ALPHA_CAMPAIGN_ID + "/contests", headers=h)
    assert r.status_code == 400
```
- [ ] **Step 2: Run → FAIL**.
- [ ] **Step 3: Implement** `backend/app/schemas/campaign.py`:
```python
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    cycle: int


class CampaignOut(BaseModel):
    id: str
    name: str
    cycle: int
    status: str
    license_tier: str
    class Config:
        from_attributes = True


class ContestCreate(BaseModel):
    cargo_id: str
    territory_id: Optional[str] = None
    election_date: Optional[date] = None


class ContestOut(BaseModel):
    id: str
    campaign_id: str
    cargo_id: str
    territory_id: Optional[str]
    election_date: Optional[date]
    class Config:
        from_attributes = True
```
`backend/app/services/campaign_service.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.campaign import Campaign, Contest, CampaignMembership


def list_my_campaigns(db: Session, ctx) -> list[Campaign]:
    if ctx.is_superadmin:
        return list(db.execute(select(Campaign).where(Campaign.deleted_at.is_(None))).scalars())
    ids = db.execute(
        select(CampaignMembership.campaign_id).where(CampaignMembership.user_id == ctx.user.id)
    ).scalars().all()
    if not ids:
        return []
    return list(db.execute(
        select(Campaign).where(Campaign.id.in_(ids), Campaign.deleted_at.is_(None))
    ).scalars())


def create_campaign(db: Session, ctx, data) -> Campaign:
    c = Campaign(name=data.name, cycle=data.cycle, organization_id=ctx.organization_id, created_by=ctx.user.id)
    db.add(c); db.flush()
    # creator is auto-enrolled as a member with their role
    db.add(CampaignMembership(user_id=ctx.user.id, campaign_id=c.id, role=ctx.role))
    db.commit(); db.refresh(c)
    return c


def list_contests(db: Session, cctx) -> list[Contest]:
    return list(db.execute(
        select(Contest).where(Contest.campaign_id == cctx.campaign_id, Contest.deleted_at.is_(None))
    ).scalars())


def create_contest(db: Session, cctx, data) -> Contest:
    ct = Contest(
        organization_id=cctx.organization_id, campaign_id=cctx.campaign_id,
        cargo_id=data.cargo_id, territory_id=data.territory_id, election_date=data.election_date,
        created_by=cctx.user.id,
    )
    db.add(ct); db.commit(); db.refresh(ct)
    return ct
```
`backend/app/routers/campaigns.py`:
```python
from typing import Annotated
from fastapi import APIRouter, Depends
from app.dependencies import CampaignCtx, DbSession, Tenant, require_roles
from app.models.user import UserRole
from app.schemas.campaign import CampaignCreate, CampaignOut, ContestCreate, ContestOut
from app.services import campaign_service as svc

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])
AdminCtx = Annotated[object, Depends(require_roles(UserRole.ADMIN))]


@router.get("/mine", response_model=list[CampaignOut])
def my_campaigns(db: DbSession, ctx: Tenant):
    return svc.list_my_campaigns(db, ctx)


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(data: CampaignCreate, db: DbSession, ctx: AdminCtx):
    return svc.create_campaign(db, ctx, data)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: str, db: DbSession, cctx: CampaignCtx):
    # cctx already validated membership + that campaign_id matches header.
    from app.models.campaign import Campaign
    from sqlalchemy import select
    c = db.execute(select(Campaign).where(Campaign.id == cctx.campaign_id)).scalar_one()
    return c


@router.get("/{campaign_id}/contests", response_model=list[ContestOut])
def list_contests(campaign_id: str, db: DbSession, cctx: CampaignCtx):
    return svc.list_contests(db, cctx)


@router.post("/{campaign_id}/contests", response_model=ContestOut, status_code=201)
def create_contest(campaign_id: str, data: ContestCreate, db: DbSession, cctx: CampaignCtx):
    return svc.create_contest(db, cctx, data)
```
Register in `backend/app/main.py`: import and `app.include_router(campaigns.router)` alongside the others.
- [ ] **Step 4: Seed a campaign in conftest** — in `backend/tests/conftest.py` `seed_data`, after users commit, create an Alpha campaign + membership for `admin@alpha.gov`, and export the id. Add near the top after imports: a module-level `ALPHA_CAMPAIGN_ID = "11111111-1111-1111-1111-111111111111"`. In the seed block:
```python
        from app.models.campaign import Campaign, CampaignMembership
        alpha_admin = db.execute(select(User).where(User.email == "admin@alpha.gov")).scalar_one()
        camp = Campaign(id=ALPHA_CAMPAIGN_ID, name="Alpha 2027", cycle=2027, organization_id=org_a.id)
        db.add(camp); db.flush()
        db.add(CampaignMembership(user_id=alpha_admin.id, campaign_id=camp.id, role=UserRole.ADMIN))
```
(`select` is already imported in conftest? if not, `from sqlalchemy import select`.)
- [ ] **Step 5: Run → PASS** `python3 -m pytest tests/test_campaigns.py -q`.
- [ ] **Step 6: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add backend/app/schemas/campaign.py backend/app/services/campaign_service.py backend/app/routers/campaigns.py backend/app/main.py backend/tests/conftest.py backend/tests/test_campaigns.py
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): campaigns/contests router + service (membership-gated, isolation-tested)"
```

---

### Task 6: Catalogs + Territory routers + catalog seed script

**Files:** Create `backend/app/schemas/catalog.py`, `backend/app/routers/catalogs.py`, `backend/app/routers/territory.py`, `backend/scripts/seed_catalogs.py`; Modify `backend/app/main.py`; Test `backend/tests/test_campaigns.py`.

- [ ] **Step 1: Failing test** — append:
```python
def test_catalogs_readable(client):
    h = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/catalogs/cargos", headers=h)
    assert r.status_code == 200 and isinstance(r.json(), list)
```
- [ ] **Step 2: Run → FAIL**.
- [ ] **Step 3: Implement** `backend/app/schemas/catalog.py`:
```python
from pydantic import BaseModel


class CargoOut(BaseModel):
    id: str; key: str; label: str; ambito: str; territory_level: str
    class Config: from_attributes = True


class PartyOut(BaseModel):
    id: str; key: str; name: str; short: str; color: str
    class Config: from_attributes = True
```
`backend/app/routers/catalogs.py`:
```python
from fastapi import APIRouter
from sqlalchemy import select
from app.dependencies import DbSession, Tenant
from app.models.catalog import Cargo, Party
from app.schemas.catalog import CargoOut, PartyOut

router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


@router.get("/cargos", response_model=list[CargoOut])
def list_cargos(db: DbSession, ctx: Tenant):
    return list(db.execute(select(Cargo)).scalars())


@router.get("/parties", response_model=list[PartyOut])
def list_parties(db: DbSession, ctx: Tenant):
    return list(db.execute(select(Party)).scalars())
```
`backend/app/routers/territory.py`:
```python
from typing import Optional
from fastapi import APIRouter
from sqlalchemy import or_, select
from app.dependencies import DbSession, Tenant
from app.models.electoral_area import ElectoralArea

router = APIRouter(prefix="/api/territory", tags=["territory"])


@router.get("/children")
def children(db: DbSession, ctx: Tenant, parent_id: Optional[str] = None, level: Optional[str] = None):
    stmt = select(ElectoralArea).where(
        ElectoralArea.deleted_at.is_(None),
        or_(ElectoralArea.organization_id.is_(None), ElectoralArea.organization_id == ctx.organization_id),
    )
    if parent_id:
        stmt = stmt.where(ElectoralArea.parent_id == parent_id)
    if level:
        stmt = stmt.where(ElectoralArea.level == level)
    rows = db.execute(stmt.limit(5000)).scalars()
    return [{"id": a.id, "name": a.name, "level": a.level.value, "code": a.code} for a in rows]
```
`backend/scripts/seed_catalogs.py` (mirror existing `scripts/` style — a runnable seeding script):
```python
"""Seed the global Cargo + Party catalogs. Idempotent."""
from sqlalchemy import select
from app.database import SessionLocal
from app.models.catalog import Cargo, Party, Ambito

CARGOS = [
    ("presidencia", "Presidencia de la República", Ambito.FEDERAL, "nation"),
    ("gubernatura", "Gubernatura", Ambito.ESTATAL, "estado"),
    ("senaduria", "Senaduría", Ambito.FEDERAL, "estado"),
    ("dip_federal", "Diputación Federal", Ambito.FEDERAL, "distrito_federal"),
    ("dip_local", "Diputación Local", Ambito.ESTATAL, "distrito_local"),
    ("presidencia_municipal", "Presidencia Municipal", Ambito.MUNICIPAL, "municipio"),
]
PARTIES = [
    ("morena", "Movimiento Regeneración Nacional", "MORENA", "#a6032f"),
    ("pan", "Partido Acción Nacional", "PAN", "#0851a5"),
    ("pri", "Partido Revolucionario Institucional", "PRI", "#0f8a3c"),
    ("mc", "Movimiento Ciudadano", "MC", "#f58025"),
    ("prd", "Partido de la Revolución Democrática", "PRD", "#ffcc00"),
    ("pvem", "Partido Verde Ecologista", "PVEM", "#2e9e57"),
    ("pt", "Partido del Trabajo", "PT", "#d62828"),
]


def run():
    with SessionLocal() as db:
        for key, label, ambito, lvl in CARGOS:
            if not db.execute(select(Cargo).where(Cargo.key == key)).scalar_one_or_none():
                db.add(Cargo(key=key, label=label, ambito=ambito, territory_level=lvl))
        for key, name, short, color in PARTIES:
            if not db.execute(select(Party).where(Party.key == key)).scalar_one_or_none():
                db.add(Party(key=key, name=name, short=short, color=color))
        db.commit()


if __name__ == "__main__":
    run()
```
Register catalogs + territory routers in `app/main.py`.
- [ ] **Step 4: Seed catalogs in conftest** — in `seed_data`, add a couple of cargos so the endpoint returns non-empty (or call a subset). Minimal: `db.add(Cargo(key="gubernatura", label="Gubernatura", ambito=Ambito.ESTATAL, territory_level="estado"))` (import `Cargo, Ambito`).
- [ ] **Step 5: Run → PASS**.
- [ ] **Step 6: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add backend/app/schemas/catalog.py backend/app/routers/catalogs.py backend/app/routers/territory.py backend/scripts/seed_catalogs.py backend/app/main.py backend/tests/conftest.py backend/tests/test_campaigns.py
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): catalogs + territory routers + catalog seed script"
```

---

### Task 7: Alembic — setup, baseline, SP0a migration, bootstrap switch

**Files:** Create `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/0001_baseline.py`, `backend/migrations/versions/0002_sp0a_spine.py`; Modify `backend/app/bootstrap.py`, `backend/requirements*.txt` (add `alembic`).

- [ ] **Step 1: Add alembic dep + init structure.** Add `alembic` to backend requirements. Create `backend/alembic.ini` (standard) with `script_location = migrations` and no hardcoded URL. Create `backend/migrations/env.py` that imports `from app.database import Base` + `import app.models` (register metadata) and reads the URL from `app.core.config.settings.DATABASE_URL`; set `target_metadata = Base.metadata`; standard online/offline runners.
- [ ] **Step 2: Baseline revision** `0001_baseline.py` — `revision="0001"`, `down_revision=None`. Its `upgrade()` creates the PRE-SP0a tables exactly as they exist today (organizations, users, electoral_areas[old columns: name/code/level/geometry/organization_id NOT NULL], audit_logs). Use `op.create_table(...)` mirroring current columns. For the geometry column on Postgres use `geoalchemy2.Geometry`; guard with a dialect check so SQLite/offline still parses. (This stamps existing prod DBs; on a fresh DB it builds the baseline.)
- [ ] **Step 3: SP0a revision** `0002_sp0a_spine.py` — `revision="0002"`, `down_revision="0001"`. `upgrade()`:
  - `op.create_table` for cargos, parties, coalitions, coalition_parties, campaigns, contests, campaign_memberships (columns per the models in Tasks 1–2; enums via `sa.Enum(..., name=...)`).
  - `op.add_column("electoral_areas", ...)` for parent_id, estado_id, municipio_id, distrito_federal_id, distrito_local_id, seccion_id (all nullable String(36) FKs).
  - Make `electoral_areas.organization_id` nullable: `op.alter_column("electoral_areas", "organization_id", nullable=True)`.
  - Extend the `area_level` enum with the new values. **Postgres:** `op.execute("ALTER TYPE area_level ADD VALUE IF NOT EXISTS 'estado'")` (one per new value; ADD VALUE can't run inside a transaction on older PG — use `op.get_bind()` autocommit block or `ALTER TYPE ... ADD VALUE` with `IF NOT EXISTS`). Document this PG caveat in the revision.
  - **Data migration:** promote the seeded base cartography to global — `op.execute("UPDATE electoral_areas SET organization_id = NULL WHERE level IN ('state','municipality')")` (the existing seed levels). Log/verify counts.
  `downgrade()`: reverse (drop new tables/columns; note enum value removal isn't supported in PG — document that downgrade leaves the extra enum values).
- [ ] **Step 4: Bootstrap switch** — edit `backend/app/bootstrap.py`: replace `_create_tables()` (`Base.metadata.create_all`) on the **Postgres** path with running Alembic to head:
```python
def _migrate() -> None:
    if engine.dialect.name != "postgresql":
        Base.metadata.create_all(engine)  # SQLite/dev keeps create_all
        return
    from alembic import command
    from alembic.config import Config
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    logger.info("Alembic migrated to head")
```
Call `_migrate()` where `_create_tables()` was called in `run_bootstrap()`.
- [ ] **Step 5: Verify** — `cd backend && alembic upgrade head` against a scratch Postgres (or `sqlite:///./scratch.db`): tables created. `alembic downgrade -1` then `upgrade head` round-trips. Run full suite `python3 -m pytest -q` (tests still use conftest create_all — unaffected). Expected: all green.
- [ ] **Step 6: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add backend/alembic.ini backend/migrations backend/app/bootstrap.py backend/requirements*.txt
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): Alembic (baseline + spine migration) replacing create_all on Postgres"
```

---

### Task 8: Frontend — campaignStore + axios header + campaign switcher + admin screen

**Files:** Create `frontend/src/store/campaignStore.ts`, `frontend/src/components/layout/CampaignSwitcher.tsx`, `frontend/src/modules/campaigns/CampaignsPage.tsx`; Modify `frontend/src/api/client.ts`, `frontend/src/components/layout/Topbar.tsx`, `frontend/src/modules/registry.ts`.

- [ ] **Step 1: campaignStore** — `frontend/src/store/campaignStore.ts` (zustand, mirrors themeStore): state `{ activeId: string | null, campaigns: {id,name,cycle,status}[] }`, `setActive(id)` (persist to `localStorage["agora-campaign"]`), `setCampaigns(list)`. On init read persisted id.
- [ ] **Step 2: axios interceptor** — in `frontend/src/api/client.ts`, add a request interceptor that sets `X-Campaign-Id` from `useCampaignStore.getState().activeId` when present (mirror how the auth token interceptor works).
- [ ] **Step 3: CampaignSwitcher** — `frontend/src/components/layout/CampaignSwitcher.tsx`: on mount fetch `/api/campaigns/mine`, populate the store, render a `<select>` (or a SegmentedControl if ≤4) bound to `activeId`; changing it calls `setActive`. Accessible (`aria-label="Campaña activa"`, focus-ring). If no active id and campaigns exist, default to the first.
- [ ] **Step 4: Mount in Topbar** — render `<CampaignSwitcher />` in the Topbar right cluster, before `<ThemeToggle />`.
- [ ] **Step 5: Admin CampaignsPage** — `frontend/src/modules/campaigns/CampaignsPage.tsx`: list campaigns (DataTable), create (Modal → POST `/api/campaigns`), and per-campaign contests (list/create). Reuse `PageHeader`/`DataTable`/`Modal`/`DataState`. Register in `registry.ts` under `administracion`, `roles: ["superadmin","admin"]`, path `/campaigns`.
- [ ] **Step 6: Verify** — build clean (`npm run lint && npm run build`); manual: log in, switcher lists campaigns, selecting one sets `X-Campaign-Id` (check Network), admin page CRUD works. Dark+light both fine (design system reused).
- [ ] **Step 7: Commit**
```bash
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence add frontend/src/store/campaignStore.ts frontend/src/components/layout/CampaignSwitcher.tsx frontend/src/modules/campaigns/ frontend/src/api/client.ts frontend/src/components/layout/Topbar.tsx frontend/src/modules/registry.ts
git -C /mnt/c/Users/ecamp/Devs/agora-civic-intelligence commit -m "feat(sp0a): frontend campaign store + switcher + admin (X-Campaign-Id wired)"
```

---

### Task 9: Final gate + isolation hardening + memory

- [ ] **Step 1: Full backend suite** — `cd backend && python3 -m pytest -q` → all green (existing + new). Confirm the isolation tests (cross-tenant/cross-campaign return empty/403) pass.
- [ ] **Step 2: Add a dedicated cross-campaign isolation test** in `tests/test_scoping.py` driving the HTTP surface: seed a second campaign under org_b; assert `admin@beta.gov` with beta's `X-Campaign-Id` cannot read alpha's contests and vice-versa (404/403/empty). Run → PASS.
- [ ] **Step 3: Frontend build gate** — `cd frontend && rm -rf dist && find . -maxdepth 1 -name '*.tsbuildinfo' -delete; npm run lint && npm run build` → PASS.
- [ ] **Step 4: Alembic round-trip** on scratch Postgres: `alembic upgrade head && alembic downgrade base && alembic upgrade head` → clean.
- [ ] **Step 5: Update memory** — write `memory/sp0a-spine.md` (architecture: Campaign/Contest, CampaignMembership, CampaignMixin, scoped_query chokepoint, X-Campaign-Id context, territory global-reference via nullable org + redundant FKs, Alembic now in use, campaign switcher) + MEMORY.md pointer. Note SP0b/SP0c are next.
- [ ] **Step 6: Hand back** — present the branch for the merge-to-main + deploy decision (Railway runs `alembic upgrade head` at startup on the Postgres path; the SP0a migration's enum-ADD-VALUE + data-migration run there — verify on first deploy). Do NOT push without user say-so.

---

## Self-Review (completed during authoring)
- **Spec coverage:** §5.1 catalog→T1, campaign/contest/membership+mixin→T2; §5.2 territory→T3; §5.3 scoping+context→T4; §5.4 Alembic→T7; §5.5 routers→T5/T6; §5.6 frontend→T8; §6 data flow exercised by T5/T8; §7 edge cases: missing/invalid header (T4/T5 tests), nullable-tenant reference union (T4/T6), data migration (T7), SQLite path (conftest create_all kept), cascade (model FKs), backward-compat (additive, existing routers untouched); §8 testing→per-task pytest + T9 isolation; §9 rollout→task order.
- **Placeholder scan:** no TBD/TODO. Alembic revision bodies (T7) describe exact `op.*` operations + the PG enum/`ADD VALUE` and data-migration SQL concretely rather than full 200-line files — this is the one place the engineer writes mechanical migration code from the explicit operation list (the models in T1–T3 are the source of truth for columns).
- **Type/name consistency:** `scoped_query(model, ctx)`, `CampaignContext.campaign_id`, `get_campaign_context`/`CampaignCtx`, `X-Campaign-Id`, `ALPHA_CAMPAIGN_ID`, `CampaignStatus`/`LicenseTier`, `CampaignMixin.campaign_id`, model/table names consistent across tasks. `ElectoralArea` drops `TenantMixin` (T3) → its `organization_id` is the nullable one referenced by `scoped_query`'s reference branch (T4) — consistent.
- **Known caveat surfaced:** Postgres `ALTER TYPE ... ADD VALUE` can't run inside a transaction on older PG — flagged in T7 for the implementer; on Railway it runs at startup via bootstrap.
