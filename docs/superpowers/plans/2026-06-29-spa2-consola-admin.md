# SPA-2 · Consola Admin / Superadmin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar la consola admin/superadmin sobre la captura de SPA-1: API admin (`/admin/registros`, `/admin/metricas`, `/admin/estructura`, `revelar-clave` auditado, `/admin/auditoria`), asignación de estructura líder→activista en `/users`, y el dashboard admin (tablero recharts, tabla con filtros + reveal, gestión de estructura), con modo consolidado cross-tenant para el superadmin.

**Architecture:** Capa admin nueva **sin cambios de esquema** reutilizando todo SPA-1: `Registro`, `User` (LIDER/ACTIVISTA/`lider_id`/`seccion`), `crypto.decrypt_clave`, `scoped_query` (bypass superadmin), `registro_service._role_scoped`, `audit_service`, `require_roles`. Backend: `dependencies` (contexto admin) → `schemas/admin` → `services/admin_service` → `routers/admin` (+ extensión de `users`). Frontend React/TS con module registry, `useAsync`/`DataState`, `recharts` (ya dependencia).

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · Pydantic v2 · `cryptography` (Fernet, ya instalado) · React 18 + TS + Vite + Tailwind + Zustand + recharts.

## Global Constraints

- **Spec de referencia:** `docs/superpowers/specs/2026-06-29-spa2-consola-admin-design.md`. Toda tarea hereda sus reglas.
- **Golden Rules (`docs/architecture.md`):** queries filtran por `organization_id`/`campaign_id` desde el contexto (nunca del body); endpoints devuelven Pydantic, nunca ORM; RBAC en la capa API vía `require_roles`; operaciones sensibles emiten `AuditLog`; nada de secretos hardcodeados; listas `{items,total,limit,offset}`; errores `{ "error": { "message", "status" } }`.
- **Sin migración:** SPA-2 **no** añade tablas/columnas. Si una decisión futura lo exigiera, `down_revision = "0008"` (head de la rama SPA-1) — pero no en este slice.
- **Reveal = audit obligatorio:** `revelar-clave` llama `crypto.decrypt_clave` **y** `record_audit("registro.reveal_clave", organization_id=<org del registro>)` en la misma transacción; **admin/superadmin only**.
- **Enmascarado por defecto:** ningún listado/métrica/estructura descifra; solo `clave_masked`.
- **Scope por rol:** reusar `registro_service._role_scoped(ctx)` (ya maneja activista/líder/admin/superadmin). No duplicar.
- **Tests:** SQLite in-memory (`backend/tests/conftest.py`) — el seed ya incluye `admin@alpha.gov`, `lider@alpha.gov`, `activista1/2@alpha.gov`, `super@atlas.gov`, `activista_beta@beta.gov`, campañas `ALPHA_CAMPAIGN_ID`/`BETA_CAMPAIGN_ID`. `auth_headers(client, email)` ya funciona (alias `email`). Suite completa verde, sin regresiones. Frontend: `npm run build` verde.
- **Rama:** trabajar sobre `feat/spa1-captura-activistas` (o una rama hija). El head Alembic en esa rama es `0008`.

---

## File Structure

**Backend — crear:**
- `backend/app/schemas/admin.py` — schemas de la consola.
- `backend/app/services/admin_service.py` — listado admin, métricas, estructura, reveal.
- `backend/app/routers/admin.py` — endpoints `/admin/*`.
- `backend/tests/test_admin_context.py`, `tests/test_admin_registros.py`, `tests/test_admin_metricas.py`, `tests/test_admin_reveal.py`, `tests/test_admin_estructura.py` — tests nuevos.

**Backend — modificar:**
- `backend/app/dependencies.py` — `get_admin_context` + `AdminCtx`.
- `backend/app/schemas/user.py` — `UserCreate`/`UserUpdate` + `lider_id`/`seccion`; `UserRead` expone `lider_id`/`seccion`.
- `backend/app/services/users_service.py` — validar/persistir `lider_id`/`seccion`.
- `backend/app/main.py` — registrar router `admin`.
- `backend/tests/test_users.py` — tests de asignación de estructura (extender).

**Frontend — crear:**
- `frontend/src/api/admin.ts` — cliente API + tipos.
- `frontend/src/modules/admin/AdminDashboardPage.tsx`
- `frontend/src/modules/admin/AdminRegistrosPage.tsx`
- `frontend/src/modules/admin/AdminEstructuraPage.tsx`

**Frontend — modificar:**
- `frontend/src/modules/registry.ts` — registrar módulos admin.
- `frontend/src/store/campaignStore.ts` + `frontend/src/components/layout/CampaignSwitcher.tsx` — opción "Todas las bases (consolidado)" (solo superadmin).

---

## Task 1: Contexto admin (`get_admin_context` / `AdminCtx`)

**Files:**
- Modify: `backend/app/dependencies.py`
- Create: `backend/tests/test_admin_context.py`

**Interfaces:**
- Consumes: `get_campaign_context`, `CampaignContext`, `Tenant`, `Header`.
- Produces: `get_admin_context(db, ctx, x_campaign_id) -> CampaignContext`; `AdminCtx = Annotated[CampaignContext, Depends(get_admin_context)]`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_admin_context.py`:
```python
"""Tests for get_admin_context: consolidated superadmin vs base-scoped."""
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.dependencies import AdminCtx
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID


def _probe_app():
    app = FastAPI()

    @app.get("/api/_probe")
    def probe(ctx: AdminCtx):
        return {"org": ctx.organization_id, "camp": ctx.campaign_id, "super": ctx.is_superadmin}

    return app


def test_superadmin_no_base_is_consolidated(client):
    from app.main import app  # reuse error handlers / DI graph
    # superadmin without X-Campaign-Id → consolidated (org None)
    h = auth_headers(client, "super@atlas.gov")
    # mount probe on the running app is overkill; assert via a real admin endpoint in later tasks.
    # Here we assert the dependency directly:
    from app.dependencies import get_admin_context, get_tenant_context, get_current_user
    # direct unit call
    import app.dependencies as deps
    # Build a TenantContext for the superadmin via the service layer:
    from sqlalchemy import select
    from app.models.user import User
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        su = db.execute(select(User).where(User.email == "super@atlas.gov")).scalar_one()
        from app.dependencies import TenantContext
        tctx = TenantContext(user=su, organization_id=None, role=su.role)
        ctx = deps.get_admin_context(db, tctx, None)
        assert ctx.organization_id is None
        assert ctx.campaign_id == ""
        assert ctx.is_superadmin
    finally:
        db.close()


def test_superadmin_with_base_adopts_org(client):
    from sqlalchemy import select
    from app.models.user import User
    from app.dependencies import TenantContext, get_admin_context
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        su = db.execute(select(User).where(User.email == "super@atlas.gov")).scalar_one()
        tctx = TenantContext(user=su, organization_id=None, role=su.role)
        ctx = get_admin_context(db, tctx, ALPHA_CAMPAIGN_ID)
        assert ctx.organization_id is not None  # adopted from the campaign's org
        assert ctx.campaign_id == ALPHA_CAMPAIGN_ID
    finally:
        db.close()
```
(Si `TestingSessionLocal` no está exportado en conftest, usar el patrón ya presente en `tests/test_registros.py` para abrir sesión; ajustar import en consecuencia.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_admin_context.py -v`
Expected: FAIL (ImportError: `AdminCtx` / `get_admin_context` no existen).

- [ ] **Step 3: Implement**

En `backend/app/dependencies.py`, tras `get_campaign_context` / `CampaignCtx`, añadir:
```python
def get_admin_context(
    db: DbSession,
    ctx: Tenant,
    x_campaign_id: Annotated[Optional[str], Header(alias="X-Campaign-Id")] = None,
) -> CampaignContext:
    """Admin/console context.

    - Superadmin with NO base selected → consolidated mode: organization_id=None,
      campaign_id="" (scoped_query then returns the cross-tenant view).
    - Anyone else (or superadmin WITH a base) → delegates to get_campaign_context,
      which mandates a valid X-Campaign-Id and adopts the base's org for superadmin.
    """
    if ctx.is_superadmin and not x_campaign_id:
        return CampaignContext(user=ctx.user, organization_id=None, role=ctx.role, campaign_id="")
    return get_campaign_context(db, ctx, x_campaign_id)


AdminCtx = Annotated[CampaignContext, Depends(get_admin_context)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_admin_context.py -v`
Expected: PASS.

- [ ] **Step 5: No regressions**

Run: `cd backend && pytest -q`
Expected: PASS (aditivo, no toca `get_campaign_context`).

- [ ] **Step 6: Commit**
```bash
git add backend/app/dependencies.py backend/tests/test_admin_context.py
git commit -m "feat(spa2): get_admin_context — consolidated superadmin vs base-scoped admin"
```

---

## Task 2: Schemas admin + `admin_service.list_admin_registros`

**Files:**
- Create: `backend/app/schemas/admin.py`
- Create: `backend/app/services/admin_service.py`
- Create: `backend/tests/test_admin_registros.py`

**Interfaces:**
- Consumes: `Registro`, `User`, `Organization`, `registro_service._role_scoped`, `CampaignContext`.
- Produces: schemas (`AdminRegistroRead`, `AdminRegistroList`, `MetricBucket`, `DailyPoint`, `MetricsRead`, `EstructuraActivista`, `EstructuraNode`, `RevelarClaveResponse`); `admin_service.list_admin_registros(db, ctx, *, q, lider_id, activista_id, seccion, since, until, limit, offset) -> tuple[list[dict], int]`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_admin_registros.py`:
```python
"""Service-level tests for admin listing with filters + base column."""
from app.models.registro import Registro
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID, BETA_CAMPAIGN_ID


def _camp_ctx(db, email, campaign_id):
    from sqlalchemy import select
    from app.dependencies import CampaignContext
    from app.models.user import User
    from app.models.campaign import Campaign
    user = db.execute(select(User).where(User.email == email)).scalar_one()
    camp = db.execute(select(Campaign).where(Campaign.id == campaign_id)).scalar_one()
    org = camp.organization_id if user.role.value == "superadmin" else user.organization_id
    return CampaignContext(user=user, organization_id=org, role=user.role, campaign_id=campaign_id)


def _consolidated_ctx(db):
    from sqlalchemy import select
    from app.dependencies import CampaignContext
    from app.models.user import User
    su = db.execute(select(User).where(User.email == "super@atlas.gov")).scalar_one()
    return CampaignContext(user=su, organization_id=None, role=su.role, campaign_id="")


def _make(db, ctx, nombre, **kw):
    from app.services import registro_service
    from app.schemas.registro import RegistroCreate
    return registro_service.create_registro(db, ctx, RegistroCreate(nombre_completo=nombre, consentimiento=True, **kw))


def test_admin_sees_full_campaign_with_base():
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        a2 = _camp_ctx(db, "activista2@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P A1", seccion="0001")
        _make(db, a2, "P A2", seccion="0002")
        rows, total = admin_service.list_admin_registros(db, admin, q=None, lider_id=None,
            activista_id=None, seccion=None, since=None, until=None, limit=50, offset=0)
        assert total == 2
        assert all(r["organization_name"] for r in rows)  # base column present
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_superadmin_consolidated_sees_multiple_orgs():
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        ab = _camp_ctx(db, "activista_beta@beta.gov", BETA_CAMPAIGN_ID)
        _make(db, a1, "Alpha P")
        _make(db, ab, "Beta P")
        rows, total = admin_service.list_admin_registros(db, _consolidated_ctx(db), q=None, lider_id=None,
            activista_id=None, seccion=None, since=None, until=None, limit=50, offset=0)
        assert total == 2
        assert len({r["organization_name"] for r in rows}) >= 2
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_filter_by_seccion():
    from app.services import admin_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P1", seccion="0001")
        _make(db, a1, "P2", seccion="0002")
        rows, total = admin_service.list_admin_registros(db, admin, q=None, lider_id=None,
            activista_id=None, seccion="0001", since=None, until=None, limit=50, offset=0)
        assert total == 1 and rows[0]["seccion"] == "0001"
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_admin_registros.py -v`
Expected: FAIL (ModuleNotFoundError: `app.services.admin_service`).

- [ ] **Step 3: Create schemas**

Crear `backend/app/schemas/admin.py` con todos los schemas de la spec §5 (`AdminRegistroRead`, `AdminRegistroList`, `MetricBucket`, `DailyPoint`, `MetricsRead`, `EstructuraActivista`, `EstructuraNode`, `RevelarClaveResponse`). `AdminRegistroRead` **NO** incluye `clave_elector_enc` ni clave en claro (solo `clave_masked`). Usar `BaseModel` plano (los servicios devuelven dicts ya proyectados, así que `from_attributes` no es necesario en `AdminRegistroRead`).

- [ ] **Step 4: Implement `admin_service.list_admin_registros`**

Crear `backend/app/services/admin_service.py`:
```python
"""Admin console service — read-only aggregates + audited clave reveal.

No schema changes: reuses Registro, User, Organization and the SPA-1 role-scope
helper (registro_service._role_scoped). Listings/metrics NEVER decrypt; only the
reveal endpoint does, and it always audits (Golden Rule #5).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.dependencies import CampaignContext
from app.models.organization import Organization
from app.models.registro import Registro
from app.models.user import User
from app.services.registro_service import _role_scoped


def list_admin_registros(
    db: Session, ctx: CampaignContext, *, q: Optional[str], lider_id: Optional[str],
    activista_id: Optional[str], seccion: Optional[str],
    since: Optional[datetime], until: Optional[datetime], limit: int, offset: int,
) -> tuple[list[dict], int]:
    base = _role_scoped(ctx).subquery()  # role + tenant/consolidated scope from SPA-1
    reg = aliased(Registro, base)

    act = aliased(User)            # activista (capturer)
    lid = aliased(User)           # activista's leader
    org = aliased(Organization)
    stmt = (
        select(reg, act.full_name, act.lider_id, lid.full_name, org.name)
        .select_from(reg)
        .outerjoin(act, act.id == reg.activista_id)
        .outerjoin(lid, lid.id == act.lider_id)
        .outerjoin(org, org.id == reg.organization_id)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(reg.nombre_completo.ilike(like), reg.seccion.ilike(like)))
    if activista_id:
        stmt = stmt.where(reg.activista_id == activista_id)
    if seccion:
        stmt = stmt.where(reg.seccion == seccion)
    if lider_id:
        # registros whose activista belongs to this leader (or the leader themself)
        members = select(User.id).where(User.lider_id == lider_id)
        stmt = stmt.where(or_(reg.activista_id.in_(members), reg.activista_id == lider_id))
    if since is not None:
        stmt = stmt.where(reg.created_at >= since)
    if until is not None:
        stmt = stmt.where(reg.created_at <= until)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(reg.created_at.desc()).limit(limit).offset(offset)
    ).all()

    out: list[dict] = []
    for r, act_name, act_lider_id, lider_name, org_name in rows:
        out.append({
            "id": r.id, "organization_id": r.organization_id, "organization_name": org_name,
            "campaign_id": r.campaign_id, "activista_id": r.activista_id, "activista_nombre": act_name,
            "lider_id": act_lider_id, "lider_nombre": lider_name,
            "nombre_completo": r.nombre_completo, "seccion": r.seccion, "colonia": r.colonia,
            "area": r.area, "telefono": r.telefono, "clave_masked": r.clave_masked,
            "consentimiento": r.consentimiento, "consentimiento_at": r.consentimiento_at,
            "created_at": r.created_at,
        })
    return out, int(total)
```
> Nota: `_role_scoped(ctx)` ya aplica soft-delete, tenant/campaign y scope por rol (incluido consolidado del superadmin). Si `aliased(Registro, subquery)` complica el join, alternativa equivalente: tomar los `ids` válidos vía `_role_scoped` y construir el select principal con `Registro.id.in_(subquery)`. Elegir la que deje el test verde y el SQL legible.

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_admin_registros.py -v`
Expected: PASS (admin full-campaign + base, consolidado multi-org, filtro sección).

- [ ] **Step 6: Commit**
```bash
git add backend/app/schemas/admin.py backend/app/services/admin_service.py backend/tests/test_admin_registros.py
git commit -m "feat(spa2): admin schemas + admin_service.list_admin_registros (filters + base column)"
```

---

## Task 3: `admin_service` — métricas + estructura

**Files:**
- Modify: `backend/app/services/admin_service.py`
- Create: `backend/tests/test_admin_metricas.py`, `backend/tests/test_admin_estructura.py`

**Interfaces:**
- Produces: `metrics(db, ctx) -> dict` (con `total`, `por_lider`, `por_activista`, `por_seccion`, `avance_diario`); `estructura(db, ctx) -> list[dict]` (árbol líder→activistas con conteos).

- [ ] **Step 1: Write the failing tests**

Crear `backend/tests/test_admin_metricas.py` (reusar helpers `_camp_ctx`/`_make` copiando del test de la Task 2 o importándolos):
```python
def test_metricas_totals_and_daily():
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx, _make, ALPHA_CAMPAIGN_ID
    from app.models.registro import Registro
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P1", seccion="0001")
        _make(db, a1, "P2", seccion="0001")
        m = admin_service.metrics(db, admin)
        assert m["total"] == 2
        assert any(b["total"] == 2 for b in m["por_activista"])
        assert any(b["key"] == "0001" and b["total"] == 2 for b in m["por_seccion"])
        assert sum(p["total"] for p in m["avance_diario"]) == 2
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
```
Crear `backend/tests/test_admin_estructura.py`:
```python
def test_estructura_tree_counts():
    from app.services import admin_service
    from tests.test_admin_registros import _camp_ctx, _make, ALPHA_CAMPAIGN_ID
    from app.models.registro import Registro
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "P1")
        tree = admin_service.estructura(db, admin)
        # lider@alpha.gov has activista1 + activista2 under them
        lider_node = next(n for n in tree if n["lider_nombre"] == "Alpha Líder")
        assert {a["nombre"] for a in lider_node["activistas"]} >= {"Alpha Activista 1", "Alpha Activista 2"}
        a1_node = next(a for a in lider_node["activistas"] if a["nombre"] == "Alpha Activista 1")
        assert a1_node["registros_count"] == 1
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_admin_metricas.py tests/test_admin_estructura.py -v`
Expected: FAIL (`metrics`/`estructura` no existen).

- [ ] **Step 3: Implement metrics**

Añadir a `admin_service.py`:
```python
def metrics(db: Session, ctx: CampaignContext) -> dict:
    base = _role_scoped(ctx).subquery()
    reg = aliased(Registro, base)
    act = aliased(User)

    total = db.execute(select(func.count()).select_from(reg)).scalar_one()

    por_activista = [
        {"key": rid, "label": name or rid or "—", "total": int(n)}
        for rid, name, n in db.execute(
            select(reg.activista_id, act.full_name, func.count())
            .select_from(reg).outerjoin(act, act.id == reg.activista_id)
            .group_by(reg.activista_id, act.full_name).order_by(func.count().desc())
        ).all()
    ]
    por_lider = [
        {"key": lid or "—", "label": lname or "Sin líder", "total": int(n)}
        for lid, lname, n in db.execute(
            select(act.lider_id, _lider_name_subq(), func.count())  # see note
            .select_from(reg).outerjoin(act, act.id == reg.activista_id)
            .group_by(act.lider_id).order_by(func.count().desc())
        ).all()
    ] if False else _por_lider(db, reg, act)  # implement via helper for the leader name join
    por_seccion = [
        {"key": s or "—", "label": s or "Sin sección", "total": int(n)}
        for s, n in db.execute(
            select(reg.seccion, func.count()).select_from(reg)
            .group_by(reg.seccion).order_by(func.count().desc())
        ).all()
    ]
    avance_diario = [
        {"fecha": str(d), "total": int(n)}
        for d, n in db.execute(
            select(func.date(reg.created_at), func.count()).select_from(reg)
            .group_by(func.date(reg.created_at)).order_by(func.date(reg.created_at))
        ).all()
    ]
    return {"total": int(total), "por_lider": por_lider, "por_activista": por_activista,
            "por_seccion": por_seccion, "avance_diario": avance_diario}
```
> Implementación concreta del leader bucket: añade un helper `_por_lider(db, reg, act)` que haga `outerjoin` de un segundo alias de `User` (`lid`) sobre `act.lider_id` y agrupe por `(act.lider_id, lid.full_name)`. Mantén la firma de salida (`key`/`label`/`total`). Borra el placeholder `if False else ...` y deja solo la llamada al helper. (El placeholder está ahí solo para señalar el join requerido.)

- [ ] **Step 4: Implement estructura**

Añadir a `admin_service.py`:
```python
def estructura(db: Session, ctx: CampaignContext) -> list[dict]:
    # Counts come from role-scoped registros; the tree (lideres/activistas) is
    # tenant-scoped by org (for a leader ctx, restrict to their own subtree).
    base = _role_scoped(ctx).subquery()
    reg = aliased(Registro, base)
    counts = dict(db.execute(
        select(reg.activista_id, func.count()).select_from(reg).group_by(reg.activista_id)
    ).all())

    lideres_q = select(User).where(User.role == UserRole.LIDER, User.deleted_at.is_(None))
    if ctx.organization_id is not None:
        lideres_q = lideres_q.where(User.organization_id == ctx.organization_id)
    if ctx.role == UserRole.LIDER and not ctx.is_superadmin:
        lideres_q = lideres_q.where(User.id == ctx.user.id)
    lideres = db.execute(lideres_q).scalars().all()

    tree = []
    for l in lideres:
        acts_q = select(User).where(User.lider_id == l.id, User.deleted_at.is_(None))
        acts = db.execute(acts_q).scalars().all()
        act_nodes = [{"id": a.id, "nombre": a.full_name, "seccion": a.seccion,
                      "registros_count": int(counts.get(a.id, 0))} for a in acts]
        tree.append({"lider_id": l.id, "lider_nombre": l.full_name, "seccion": l.seccion,
                     "registros_count": int(counts.get(l.id, 0))
                                       + sum(n["registros_count"] for n in act_nodes),
                     "activistas": act_nodes})
    return tree
```
Añadir `from app.models.user import User, UserRole` al import de `admin_service.py` si falta `UserRole`.

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_admin_metricas.py tests/test_admin_estructura.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**
```bash
git add backend/app/services/admin_service.py backend/tests/test_admin_metricas.py backend/tests/test_admin_estructura.py
git commit -m "feat(spa2): admin_service metrics (lider/activista/seccion/daily) + estructura tree"
```

---

## Task 4: `admin_service.reveal_clave` (descifrado auditado)

**Files:**
- Modify: `backend/app/services/admin_service.py`
- Create: `backend/tests/test_admin_reveal.py`

**Interfaces:**
- Consumes: `crypto.decrypt_clave`, `record_audit`, `registro_service.get_registro`.
- Produces: `reveal_clave(db, ctx, registro_id) -> Optional[str]`; `NoClave(Exception)`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_admin_reveal.py`:
```python
def test_reveal_decrypts_and_audits():
    from app.services import admin_service
    from app.models.audit_log import AuditLog
    from app.models.registro import Registro
    from sqlalchemy import select
    from tests.test_admin_registros import _camp_ctx, _make, ALPHA_CAMPAIGN_ID
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        reg = _make(db, a1, "Con Clave", clave_elector="ABCD1234567890XYZ8")
        plain = admin_service.reveal_clave(db, admin, reg.id)
        assert plain == "ABCD1234567890XYZ8"
        audit = db.execute(select(AuditLog).where(
            AuditLog.action == "registro.reveal_clave", AuditLog.entity_id == reg.id)).scalars().all()
        assert len(audit) == 1
        assert audit[0].organization_id == reg.organization_id
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_reveal_no_clave_raises():
    import pytest
    from app.services import admin_service
    from app.models.registro import Registro
    from tests.test_admin_registros import _camp_ctx, _make, ALPHA_CAMPAIGN_ID
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        admin = _camp_ctx(db, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
        reg = _make(db, a1, "Sin Clave")
        with pytest.raises(admin_service.NoClave):
            admin_service.reveal_clave(db, admin, reg.id)
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_admin_reveal.py -v`
Expected: FAIL (`reveal_clave`/`NoClave` no existen).

- [ ] **Step 3: Implement**

Añadir a `admin_service.py`:
```python
from app.core import crypto
from app.services import registro_service
from app.services.audit_service import record_audit


class NoClave(Exception):
    """Raised when a registro has no stored clave to reveal."""


def reveal_clave(db: Session, ctx: CampaignContext, registro_id: str) -> Optional[str]:
    """Decrypt the clave de elector. ALWAYS audits. Admin/superadmin only (gated at router).

    Returns the plaintext, or None if the registro is out of scope (404 at router).
    Raises NoClave (422 at router) when there is no ciphertext to reveal.
    """
    reg = registro_service.get_registro(db, ctx, registro_id)
    if reg is None:
        return None
    if not reg.clave_elector_enc:
        raise NoClave()
    plain = crypto.decrypt_clave(bytes(reg.clave_elector_enc))
    record_audit(
        db, action="registro.reveal_clave", actor_id=ctx.user.id,
        organization_id=reg.organization_id,  # target base, not the operator's
        entity_type="registro", entity_id=reg.id,
    )
    db.commit()
    return plain
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/test_admin_reveal.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/admin_service.py backend/tests/test_admin_reveal.py
git commit -m "feat(spa2): admin_service.reveal_clave — Fernet decrypt with mandatory audit"
```

---

## Task 5: Router `/admin/*` + registro en main + tests de API/permisos

**Files:**
- Create: `backend/app/routers/admin.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_admin_api.py`

**Interfaces:**
- Consumes: `admin_service`, schemas de `admin`, `AdminCtx`, `Tenant`, `require_roles`, `audit_service`.
- Produces: `GET /admin/registros`, `GET /admin/metricas`, `GET /admin/estructura`, `POST /admin/registros/{id}/revelar-clave`, `GET /admin/auditoria`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_admin_api.py`:
```python
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID, BETA_CAMPAIGN_ID


def _hdr(client, email, campaign_id=None):
    h = auth_headers(client, email)
    if campaign_id:
        h["X-Campaign-Id"] = campaign_id
    return h


def _capture(client, email, **body):
    h = _hdr(client, email, ALPHA_CAMPAIGN_ID)
    r = client.post("/api/registros", json={"consentimiento": True, **body}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_admin_registros_lists_with_base(client):
    _capture(client, "activista1@alpha.gov", nombre_completo="Para Admin", seccion="0001")
    resp = client.get("/api/admin/registros", headers=_hdr(client, "admin@alpha.gov", ALPHA_CAMPAIGN_ID))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert "organization_name" in body["items"][0]
    assert "clave_elector" not in body["items"][0]


def test_activista_forbidden_on_admin(client):
    resp = client.get("/api/admin/registros", headers=_hdr(client, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID))
    assert resp.status_code == 403


def test_metricas_and_estructura(client):
    _capture(client, "activista1@alpha.gov", nombre_completo="M", seccion="0001")
    h = _hdr(client, "admin@alpha.gov", ALPHA_CAMPAIGN_ID)
    assert client.get("/api/admin/metricas", headers=h).status_code == 200
    assert client.get("/api/admin/estructura", headers=h).status_code == 200


def test_reveal_admin_only_and_audited(client):
    rid = _capture(client, "activista1@alpha.gov", nombre_completo="Rev", clave_elector="ABCD1234567890XYZ8")
    # lider cannot reveal
    bad = client.post(f"/api/admin/registros/{rid}/revelar-clave",
                      headers=_hdr(client, "lider@alpha.gov", ALPHA_CAMPAIGN_ID))
    assert bad.status_code == 403
    # admin can
    ok = client.post(f"/api/admin/registros/{rid}/revelar-clave",
                     headers=_hdr(client, "admin@alpha.gov", ALPHA_CAMPAIGN_ID))
    assert ok.status_code == 200, ok.text
    assert ok.json()["clave_elector"] == "ABCD1234567890XYZ8"
    # audit visible
    aud = client.get("/api/admin/auditoria?action=registro.reveal_clave",
                     headers=_hdr(client, "admin@alpha.gov", ALPHA_CAMPAIGN_ID))
    assert aud.status_code == 200 and aud.json()["total"] >= 1


def test_superadmin_consolidated_no_base(client):
    _capture(client, "activista1@alpha.gov", nombre_completo="Alpha row")
    # superadmin WITHOUT X-Campaign-Id → consolidated
    resp = client.get("/api/admin/registros", headers=auth_headers(client, "super@atlas.gov"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] >= 1
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_admin_api.py -v`
Expected: FAIL (404 — router no registrado).

- [ ] **Step 3: Implement the router**

Crear `backend/app/routers/admin.py`:
```python
"""Admin console router: /admin registros, metricas, estructura, reveal, auditoria."""
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import AdminCtx, DbSession, Tenant, require_roles
from app.models.user import UserRole
from app.schemas.admin import (
    AdminRegistroList, AdminRegistroRead, EstructuraNode, MetricsRead, RevelarClaveResponse,
)
from app.schemas.audit import AuditEntry
from app.schemas.pagination import Page
from app.services import admin_service, audit_service
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/admin", tags=["admin"])

# Console read access: admin + lider (lider is role-scoped to their estructura).
ConsoleCtx = Annotated[object, Depends(require_roles(UserRole.ADMIN, UserRole.LIDER))]
# Reveal + auditoria: admin only (lider/activista excluded; superadmin auto-passes).
AdminOnly = Annotated[object, Depends(require_roles(UserRole.ADMIN))]


@router.get("/registros", response_model=AdminRegistroList)
def list_registros(
    db: DbSession, ctx: AdminCtx, _perm: ConsoleCtx,
    pagination: Annotated[PaginationParams, Depends()],
    q: Optional[str] = Query(None), lider_id: Optional[str] = Query(None),
    activista_id: Optional[str] = Query(None), seccion: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None), until: Optional[datetime] = Query(None),
) -> AdminRegistroList:
    rows, total = admin_service.list_admin_registros(
        db, ctx, q=q, lider_id=lider_id, activista_id=activista_id, seccion=seccion,
        since=since, until=until, limit=pagination.limit, offset=pagination.offset)
    return AdminRegistroList(items=[AdminRegistroRead(**r) for r in rows],
                             total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/metricas", response_model=MetricsRead)
def metricas(db: DbSession, ctx: AdminCtx, _perm: ConsoleCtx) -> MetricsRead:
    return MetricsRead(**admin_service.metrics(db, ctx))


@router.get("/estructura", response_model=list[EstructuraNode])
def estructura(db: DbSession, ctx: AdminCtx, _perm: ConsoleCtx) -> list[EstructuraNode]:
    return [EstructuraNode(**n) for n in admin_service.estructura(db, ctx)]


@router.post("/registros/{registro_id}/revelar-clave", response_model=RevelarClaveResponse)
def revelar_clave(registro_id: str, db: DbSession, ctx: AdminCtx, _perm: AdminOnly) -> RevelarClaveResponse:
    try:
        plain = admin_service.reveal_clave(db, ctx, registro_id)
    except admin_service.NoClave:
        raise HTTPException(status_code=422, detail="El registro no tiene clave de elector")
    if plain is None:
        raise HTTPException(status_code=404, detail="Registro not found")
    return RevelarClaveResponse(registro_id=registro_id, clave_elector=plain)


@router.get("/auditoria", response_model=Page[AuditEntry])
def auditoria(
    ctx: Tenant, db: DbSession, _perm: AdminOnly,
    pagination: Annotated[PaginationParams, Depends()],
    action: Optional[str] = Query(None), actor: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None), until: Optional[datetime] = Query(None),
) -> Page[AuditEntry]:
    items, total = audit_service.list_events(
        db, ctx, action=action, actor=actor, entity_type=entity_type,
        since=since, until=until, limit=pagination.limit, offset=pagination.offset)
    return Page[AuditEntry](items=[AuditEntry.model_validate(i) for i in items],
                            total=total, limit=pagination.limit, offset=pagination.offset)
```
> `revelar-clave` y `auditoria` usan `AdminCtx`/`Tenant` (que ya excluye no-superadmin sin org). El gate `AdminOnly` corre alongside; `require_roles(ADMIN)` deja pasar admin y superadmin pero **no** líder. `auditoria` usa `Tenant` (no requiere base) para que el superadmin vea consolidado.

- [ ] **Step 4: Register the router in main**

En `backend/app/main.py`, en el import del bloque `from app.routers import (...)` añadir `admin,` (orden alfabético) y en `_register_routers` añadir `admin` a la tupla del `for module in (...)`.

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_admin_api.py -v`
Expected: PASS (listado+base, 403 activista, métricas/estructura, reveal admin-only+audit, consolidado superadmin).

- [ ] **Step 6: Full suite**

Run: `cd backend && pytest -q`
Expected: PASS (sin regresiones).

- [ ] **Step 7: Commit**
```bash
git add backend/app/routers/admin.py backend/app/main.py backend/tests/test_admin_api.py
git commit -m "feat(spa2): /admin router (registros, metricas, estructura, revelar-clave, auditoria)"
```

---

## Task 6: Asignación de estructura en `/users` (`lider_id` + `seccion`)  ⟂ paralelizable

> **Paralelizable** con Tasks 2–4 (toca `schemas/user.py`, `services/users_service.py`, `tests/test_users.py` — disjuntos de los archivos admin). Solo comparte conceptualmente; ejecutable en worktree aislado.

**Files:**
- Modify: `backend/app/schemas/user.py`, `backend/app/services/users_service.py`
- Modify: `backend/tests/test_users.py` (añadir)

**Interfaces:**
- Produces: `UserCreate`/`UserUpdate` con `lider_id?`/`seccion?`; `UserRead` expone `lider_id`/`seccion`; `users_service` valida y persiste.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_users.py`:
```python
def test_create_activista_with_lider_and_seccion(client):
    from tests.conftest import auth_headers
    from sqlalchemy import select
    from app.models.user import User
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    lider_id = db.execute(select(User.id).where(User.email == "lider@alpha.gov")).scalar_one()
    db.close()
    h = auth_headers(client, "admin@alpha.gov")
    resp = client.post("/api/users", json={
        "email": "nuevo.activista@alpha.gov", "full_name": "Nuevo Act",
        "role": "activista", "lider_id": lider_id, "seccion": "0007"}, headers=h)
    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["lider_id"] == lider_id
    assert resp.json()["user"]["seccion"] == "0007"


def test_lider_id_must_be_a_lider(client):
    from tests.conftest import auth_headers
    from sqlalchemy import select
    from app.models.user import User
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    not_lider = db.execute(select(User.id).where(User.email == "viewer@alpha.gov")).scalar_one()
    db.close()
    h = auth_headers(client, "admin@alpha.gov")
    resp = client.post("/api/users", json={
        "email": "x@alpha.gov", "full_name": "X", "role": "activista",
        "lider_id": not_lider}, headers=h)
    assert resp.status_code == 400, resp.text
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_users.py -k "lider or seccion" -v`
Expected: FAIL (schema ignora `lider_id`/`seccion`; no validación).

- [ ] **Step 3: Extend schemas**

En `backend/app/schemas/user.py`:
- `UserCreate`: añadir `lider_id: str | None = None` y `seccion: str | None = Field(default=None, max_length=20)`.
- `UserUpdate`: añadir `lider_id: str | None = None` y `seccion: str | None = Field(default=None, max_length=20)`.
- `UserRead`: añadir `lider_id: str | None` y `seccion: str | None`.

> Nota: para `UserUpdate`, distinguir "no enviado" de "desasignar" (`null`) requiere `model_fields_set`; el servicio usa `data.model_dump(exclude_unset=True)`-style. Mantén el patrón existente de asignación condicional (`if data.X is not None`) salvo para `lider_id`, donde queremos permitir `None` explícito → usa `"lider_id" in data.model_fields_set`.

- [ ] **Step 4: Implement validation in users_service**

En `backend/app/services/users_service.py` añadir un helper y usarlo en `create_user`/`update_user`:
```python
def _validate_lider(db, ctx, lider_id, org_id, target_id=None):
    if lider_id is None:
        return
    if lider_id == target_id:
        raise HTTPException(status_code=400, detail="A user cannot be their own leader")
    lider = db.execute(select(User).where(User.id == lider_id, User.deleted_at.is_(None))).scalar_one_or_none()
    if lider is None or lider.role != UserRole.LIDER:
        raise HTTPException(status_code=400, detail="lider_id must reference a LIDER user")
    if not ctx.is_superadmin and lider.organization_id != org_id:
        raise HTTPException(status_code=400, detail="lider_id must be in the same organization")
```
- En `create_user`: tras resolver `org_id`, llamar `_validate_lider(db, ctx, data.lider_id, org_id)` y setear `lider_id=data.lider_id, seccion=data.seccion` en el `User(...)`.
- En `update_user`: si `"lider_id" in data.model_fields_set`: `_validate_lider(db, ctx, data.lider_id, user.organization_id, target_id=user.id)` y `user.lider_id = data.lider_id`. Si `data.seccion is not None`: `user.seccion = data.seccion`. Incluir ambos en el `meta` del audit (ya usa `data.model_dump(exclude_none=True)`).

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_users.py -v`
Expected: PASS (alta con líder/sección; rechazo de líder inválido; sin regresiones en los tests previos de users).

- [ ] **Step 6: Commit**
```bash
git add backend/app/schemas/user.py backend/app/services/users_service.py backend/tests/test_users.py
git commit -m "feat(spa2): user CRUD supports estructura (lider_id + seccion) with validation"
```

---

## Task 7: Frontend — cliente API admin + tipos + registry + toggle base consolidada

**Files:**
- Create: `frontend/src/api/admin.ts`
- Modify: `frontend/src/modules/registry.ts`, `frontend/src/store/campaignStore.ts`, `frontend/src/components/layout/CampaignSwitcher.tsx`

**Interfaces:**
- Produces: `getAdminRegistros`, `getMetricas`, `getEstructura`, `revelarClave`, `getAdminAuditoria` + tipos; rutas/módulos `admin-*` en el registry; capacidad de limpiar la base activa (consolidado, superadmin).

- [ ] **Step 1: Create the API client**

Crear `frontend/src/api/admin.ts` (mirror de `frontend/src/api/registros.ts`/`audit.ts`; `apiClient` ya inyecta `Authorization` + `X-Campaign-Id`):
```typescript
import { apiClient } from "./client";
import type { UserRole } from "@/types/auth";

export interface AdminRegistro {
  id: string; organization_id: string; organization_name: string | null;
  campaign_id: string; activista_id: string | null; activista_nombre: string | null;
  lider_id: string | null; lider_nombre: string | null;
  nombre_completo: string; seccion: string | null; colonia: string | null;
  area: string | null; telefono: string | null; clave_masked: string | null;
  consentimiento: boolean; consentimiento_at: string | null; created_at: string;
}
export interface AdminRegistroList { items: AdminRegistro[]; total: number; limit: number; offset: number; }
export interface MetricBucket { key: string; label: string; total: number; }
export interface DailyPoint { fecha: string; total: number; }
export interface Metricas {
  total: number; por_lider: MetricBucket[]; por_activista: MetricBucket[];
  por_seccion: MetricBucket[]; avance_diario: DailyPoint[];
}
export interface EstructuraActivista { id: string; nombre: string; seccion: string | null; registros_count: number; }
export interface EstructuraNode {
  lider_id: string; lider_nombre: string; seccion: string | null;
  registros_count: number; activistas: EstructuraActivista[];
}
export interface AdminRegistrosParams {
  q?: string; lider_id?: string; activista_id?: string; seccion?: string;
  since?: string; until?: string; limit?: number; offset?: number;
}

export async function getAdminRegistros(p: AdminRegistrosParams): Promise<AdminRegistroList> {
  const { data } = await apiClient.get<AdminRegistroList>("/admin/registros", { params: p });
  return data;
}
export async function getMetricas(): Promise<Metricas> {
  const { data } = await apiClient.get<Metricas>("/admin/metricas");
  return data;
}
export async function getEstructura(): Promise<EstructuraNode[]> {
  const { data } = await apiClient.get<EstructuraNode[]>("/admin/estructura");
  return data;
}
export async function revelarClave(id: string): Promise<{ registro_id: string; clave_elector: string }> {
  const { data } = await apiClient.post(`/admin/registros/${id}/revelar-clave`);
  return data;
}
export type { UserRole };
```

- [ ] **Step 2: Allow clearing the active base (consolidado)**

En `frontend/src/store/campaignStore.ts`: `setActive` ya acepta y persiste; añadir un método explícito `clearActive: () => void` que llame `persistId(null); set({ activeId: null })`. (Opcional si `setActive` se adapta para aceptar `null`; preferible un método dedicado por claridad de tipos.)

En `frontend/src/components/layout/CampaignSwitcher.tsx`: para superadmin (leer `useAuthStore().user?.role === "superadmin"`), añadir como primera opción del `<select>` `value=""` con label "Todas las bases (consolidado)"; al elegirla, `clearActive()`. Para no-superadmin, comportamiento intacto.

- [ ] **Step 3: Register modules**

En `frontend/src/modules/registry.ts`: añadir lazy imports y entradas (sección `administracion` o `gobernanza`):
```typescript
const AdminDashboard = lazy(() => import("@/modules/admin/AdminDashboardPage").then((m) => ({ default: m.AdminDashboardPage })));
const AdminRegistros = lazy(() => import("@/modules/admin/AdminRegistrosPage").then((m) => ({ default: m.AdminRegistrosPage })));
const AdminEstructura = lazy(() => import("@/modules/admin/AdminEstructuraPage").then((m) => ({ default: m.AdminEstructuraPage })));
// ...
{ key: "admin-dashboard", path: "/admin", label: "Consola Activistas", section: "gobernanza", icon: AnalyticsIcon, state: "active", element: AdminDashboard, roles: ["admin", "lider", "superadmin"] },
{ key: "admin-registros", path: "/admin/registros", label: "Registros (Admin)", section: "gobernanza", icon: VotersIcon, state: "active", element: AdminRegistros, roles: ["admin", "lider", "superadmin"] },
{ key: "admin-estructura", path: "/admin/estructura", label: "Estructura", section: "administracion", icon: UserIcon, state: "active", element: AdminEstructura, roles: ["admin", "superadmin"] },
```
> Crear stubs mínimos de las 3 páginas (exportan el componente y un `AppLayout` vacío) para que el build pase; se llenan en Tasks 8–10. Alternativamente, ejecutar Tasks 8–10 antes de añadir las entradas al registry. Para mantener este task autocontenido, crea stubs.

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: verde (tipos OK, lazy imports resuelven a los stubs).

- [ ] **Step 5: Commit**
```bash
git add frontend/src/api/admin.ts frontend/src/modules/registry.ts frontend/src/store/campaignStore.ts frontend/src/components/layout/CampaignSwitcher.tsx frontend/src/modules/admin/
git commit -m "feat(spa2): admin API client + module registry + consolidated base toggle"
```

---

## Task 8: Frontend — AdminDashboardPage (tablero + recharts)  ⟂ paralelizable

> **Paralelizable** con Tasks 9 y 10 (archivos de página disjuntos). Depende de Task 7 (api/tipos/registry stubs).

**Files:**
- Modify/replace stub: `frontend/src/modules/admin/AdminDashboardPage.tsx`

- [ ] **Step 1: Implement**

`AdminDashboardPage` con `AppLayout` + `PageHeader`; `const m = useAsync(getMetricas, [])`; `DataState` envolviendo:
- `MetricCard`s: total registros (`m.data.total`), top activista (`por_activista[0]`), secciones cubiertas (`por_seccion.length`).
- **Avance diario:** `recharts` `ResponsiveContainer` + `AreaChart`/`LineChart` sobre `m.data.avance_diario` (`fecha`→X, `total`→Y).
- **Top activistas:** `BarChart` sobre `por_activista.slice(0, 10)` (`label`→categoría, `total`).
- **Cobertura por sección:** `BarChart` o `DataTable` sobre `por_seccion`.
Importar de `recharts` (ya dependencia). Reusar el patrón de uso de recharts de `AnalyticsPage`/`DashboardPage` si existe para estilos consistentes.

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: verde.

- [ ] **Step 3: Commit**
```bash
git add frontend/src/modules/admin/AdminDashboardPage.tsx
git commit -m "feat(spa2): admin dashboard — totals + daily/top-activistas/seccion charts (recharts)"
```

---

## Task 9: Frontend — AdminRegistrosPage (tabla + filtros + revelar)  ⟂ paralelizable

> **Paralelizable** con Tasks 8 y 10. Depende de Task 7.

**Files:**
- Modify/replace stub: `frontend/src/modules/admin/AdminRegistrosPage.tsx`

- [ ] **Step 1: Implement**

Mirror de `modules/auditoria/AuditoriaPage.tsx` (tabla server-paginada + filtros debounced + paginación externa):
- Estado de filtros: `q`, `seccion`, `lider_id`/`activista_id` (selects poblados desde `getEstructura` o inputs), `since`/`until` (`datetime-local` → ISO con el helper `localToIso`), `offset`.
- Carga vía `getAdminRegistros({...})` (patrón `useEffect` + `ignore` de Auditoría, o `useAsync` con deps).
- `DataTable<AdminRegistro>` con columnas: nombre, sección, activista (`activista_nombre`), líder (`lider_nombre`), **Base** (`organization_name`), `clave_masked`, fecha.
- **Revelar clave:** botón por fila visible solo si `useAuthStore().user?.role` ∈ `{admin, superadmin}`; al click → `window.confirm` → `revelarClave(id)` → mostrar la clave devuelta en un drawer/toast efímero (no persistir en estado global ni en la tabla). Manejar 422 (sin clave) / 404.
- `DataState` para loading/error/empty (`"Sin registros para los filtros seleccionados."`).

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: verde.

- [ ] **Step 3: Commit**
```bash
git add frontend/src/modules/admin/AdminRegistrosPage.tsx
git commit -m "feat(spa2): admin registros table — filters, base column, audited reveal (admin-only UI)"
```

---

## Task 10: Frontend — AdminEstructuraPage (árbol + alta/edición de usuarios)  ⟂ paralelizable

> **Paralelizable** con Tasks 8 y 9. Depende de Task 7. Reusa `frontend/src/api/users.ts` (CRUD existente) + los nuevos campos `lider_id`/`seccion`.

**Files:**
- Modify/replace stub: `frontend/src/modules/admin/AdminEstructuraPage.tsx`
- Verify/extend: `frontend/src/api/users.ts` (asegurar que los payloads de create/update incluyan `lider_id`/`seccion`).

- [ ] **Step 1: Implement**

- `const tree = useAsync(getEstructura, [])`; render del árbol: por cada `EstructuraNode` (líder) una `Card` con su `registros_count` y una lista de `activistas` (nombre, sección, `registros_count`).
- **Alta/edición de usuarios** con asignación de líder y sección: formulario que llama a `createUser`/`updateUser` (de `@/api/users`) con `role`, `lider_id` (select de líderes desde el árbol), `seccion`. Tras éxito, `tree.reload()`.
- Gate visual admin/superadmin (el módulo ya está role-gated en el registry; defensa adicional opcional).
- `DataState` para loading/error/empty (`"Aún no hay estructura configurada."`).

- [ ] **Step 2: Verify users API client carries new fields**

En `frontend/src/api/users.ts`, asegurar que los tipos `UserCreate`/`UserUpdate` y las funciones envíen `lider_id?`/`seccion?`. Añadir `lider_id`/`seccion` al tipo `User` si la página los muestra.

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: verde.

- [ ] **Step 4: Commit**
```bash
git add frontend/src/modules/admin/AdminEstructuraPage.tsx frontend/src/api/users.ts
git commit -m "feat(spa2): admin estructura tree + user create/edit with lider/seccion assignment"
```

---

## Parallelization map

- **Backend sequential core:** Task 1 → (Tasks 2 → 3 → 4 sequential, same `admin_service.py`) → Task 5.
- **Task 6** (users estructura) is **⟂ parallel** with Tasks 2–4 (disjoint files); must land before final integration but not before Task 5 strictly (Task 5 doesn't touch users). Can run in its own worktree concurrently with the admin-service chain.
- **Frontend:** Task 7 first (api/types/registry/stubs) → then **Tasks 8, 9, 10 are ⟂ parallel** (disjoint page files), each isolated in its own worktree.
- Frontend tasks (7–10) can begin against the API contract as soon as Task 5's shapes are fixed; for real end-to-end verification they need the backend merged.

## Self-Review

- [ ] **No schema/migration:** confirmar que ningún archivo bajo `backend/alembic/versions/` fue creado/modificado. SPA-2 no toca el esquema.
- [ ] **Reveal siempre audita:** `admin_service.reveal_clave` llama `crypto.decrypt_clave` **y** `record_audit("registro.reveal_clave", organization_id=reg.organization_id)` antes del `commit`; cubierto por `test_admin_reveal.py` y `test_admin_api.py`.
- [ ] **Reveal admin-only:** `require_roles(UserRole.ADMIN)` en `revelar-clave`/`auditoria` excluye `LIDER`/`ACTIVISTA`; superadmin pasa. Test 403 para líder.
- [ ] **Enmascarado por defecto:** ninguna respuesta de `/admin/registros`/`metricas`/`estructura` incluye `clave_elector_enc` ni clave en claro (solo `clave_masked`). Test asserta ausencia de `clave_elector`.
- [ ] **Scope por rol reusado:** servicios usan `registro_service._role_scoped(ctx)`; no se reimplementa el scoping.
- [ ] **Consolidado superadmin:** `get_admin_context` sin header → org None; `scoped_query` retorna vista cross-tenant; test verifica filas de ≥2 orgs y la columna `organization_name`.
- [ ] **Golden Rules:** respuestas Pydantic (nunca ORM crudo); listas `{items,total,limit,offset}`; errores con envelope (heredado de `main.py`); RBAC en API; org/campaign desde el contexto.
- [ ] **Frontend consistente con la realidad:** `useAsync`/`DataState` (NO TanStack), `recharts` (ya dependencia), `apiClient` inyecta headers; reveal UI solo para admin/superadmin.
- [ ] **Sin regresiones:** `cd backend && pytest -q` verde; `cd frontend && npm run build` verde.
- [ ] **Preguntas abiertas resueltas con el humano** antes de cerrar: UX base consolidada, `/admin/auditoria` vs `/audit`, diferimiento del catálogo de áreas, alcance de lectura del líder (spec §10).
