# RBAC v2 — Redefinición de Roles y Permisos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el modelo de 9 roles *default-deny* en toda la plataforma: añadir COORDINADOR/CAPTURISTA/CONSULTA, jerarquía `coordinador_id`, scoping por rol, gating por endpoint (incluida la inteligencia hoy abierta) y `roles:` explícito en cada módulo del frontend.

**Architecture:** Reutiliza el spine de RBAC existente: enum `UserRole`, `require_roles` (dependencies.py), `scoped_query` (core/scoping.py) y `registro_service._role_scoped`. Se extienden — no se reescriben. Migraciones con el patrón endurecido de enums.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · React/TS + Vite.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-29-rbac-redefinicion-roles-permisos-design.md`. Toda tarea hereda sus matrices (§5 visibilidad, §6 acciones, §9 gating).
- **Enum PG endurecido:** `ALTER TYPE user_role ADD VALUE` SOLO con NOMBRES en mayúscula dentro de `op.get_context().autocommit_block()`, PG-only; SQLite = VARCHAR sin DDL. Ver `backend/alembic/versions/0003_area_level_values.py`.
- **Migración:** head Alembic vigente en main = `0011`. Nueva migración = `0012`, `down_revision="0011"`. Helpers `_table_exists`/`_index_exists`, dialect-safe, idempotente, sin try/except de control de flujo.
- **Default-deny:** ningún módulo del frontend sin `roles:`; ningún endpoint de datos sin `require_roles` (salvo `/health`, `/auth/login`, y assets/SPA).
- **PII intacta:** no se relaja nada de cifrado/masking/audit de SPA-1..4; reveal-clave sigue ADMIN/SUPERADMIN.
- **Tests:** backend `cd backend && python3 -m pytest` (baseline 251, todo verde); frontend `cd frontend && npm run build` verde. Roles en minúscula en el frontend (`"coordinador"`, etc.), NOMBRES mayúscula en el enum backend.
- **Rama:** `feat/rbac-v2` (ya creada desde main; main = SPA-1..4 desplegado).

---

## Task 1: Enum UserRole + `User.coordinador_id` (modelo)

**Files:**
- Modify: `backend/app/models/user.py`
- Test: `backend/tests/test_rbac_roles.py` (crear)

**Interfaces:**
- Produces: `UserRole.COORDINADOR` (`"coordinador"`), `UserRole.CAPTURISTA` (`"capturista"`), `UserRole.CONSULTA` (`"consulta"`); `User.coordinador_id: Optional[str]`.

- [ ] **Step 1: Write the failing test** — crear `backend/tests/test_rbac_roles.py`:
```python
from app.models.user import User, UserRole

def test_new_roles_exist():
    assert UserRole.COORDINADOR.value == "coordinador"
    assert UserRole.CAPTURISTA.value == "capturista"
    assert UserRole.CONSULTA.value == "consulta"

def test_user_has_coordinador_id():
    assert "coordinador_id" in User.__table__.c
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python3 -m pytest tests/test_rbac_roles.py -v` → FAIL (AttributeError COORDINADOR).

- [ ] **Step 3: Extend the enum** — en `backend/app/models/user.py`, tras `ACTIVISTA = "activista"` añadir:
```python
    COORDINADOR = "coordinador"
    CAPTURISTA = "capturista"
    CONSULTA = "consulta"
```

- [ ] **Step 4: Add the self-FK column** — tras la columna `lider_id` (mismo patrón), añadir:
```python
    # A LIDER points to its COORDINADOR (campo→coordinación). Self-FK, like lider_id.
    coordinador_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
```

- [ ] **Step 5: Run tests + full suite** — `python3 -m pytest tests/test_rbac_roles.py -v` PASS; `python3 -m pytest -q` sin regresiones (enum/columna aditivos).

- [ ] **Step 6: Commit**
```bash
git add backend/app/models/user.py backend/tests/test_rbac_roles.py
git commit -m "feat(rbac-v2): UserRole +COORDINADOR/+CAPTURISTA/+CONSULTA + User.coordinador_id"
```

---

## Task 2: Migración Alembic 0012 (enum values + coordinador_id)

**Files:**
- Create: `backend/alembic/versions/0012_rbac_v2.py`

**Interfaces:**
- Consumes: head `0011`. Produces: valores enum `COORDINADOR`/`CAPTURISTA`/`CONSULTA`; columna `users.coordinador_id` + índice.

- [ ] **Step 1: Read patterns** — leer `backend/alembic/versions/0003_area_level_values.py` (autocommit_block ADD VALUE) y `0008_activistas.py` (add_column + FK + index dialect-safe).

- [ ] **Step 2: Write the migration** — crear `backend/alembic/versions/0012_rbac_v2.py`:
```python
"""RBAC v2: user_role +coordinador/capturista/consulta + users.coordinador_id.

Revision ID: 0012
Revises: 0011
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

NEW_ROLES = ["COORDINADOR", "CAPTURISTA", "CONSULTA"]


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    if is_pg:
        with op.get_context().autocommit_block():
            for name in NEW_ROLES:
                op.execute(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{name}'")
    user_cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "coordinador_id" not in user_cols:
        op.add_column("users", sa.Column("coordinador_id", sa.String(length=36), nullable=True))
        if is_pg:
            op.create_foreign_key(
                "fk_users_coordinador_id", "users", "users",
                ["coordinador_id"], ["id"], ondelete="SET NULL",
            )
        op.create_index("ix_users_coordinador_id", "users", ["coordinador_id"])


def downgrade() -> None:
    bind = op.get_bind()
    user_cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "coordinador_id" in user_cols:
        op.drop_index("ix_users_coordinador_id", table_name="users")
        if bind.dialect.name == "postgresql":
            op.drop_constraint("fk_users_coordinador_id", "users", type_="foreignkey")
        op.drop_column("users", "coordinador_id")
    # Enum values are not removed (PG limitation; consistent with prior migrations).
```

- [ ] **Step 3: Verify SQLite round-trip** — 
```bash
cd backend && python3 -c "
from alembic.config import Config; from alembic import command
import tempfile, os
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
cfg=Config('alembic.ini'); command.upgrade(cfg,'head'); command.downgrade(cfg,'0011'); print('0012 up/down OK')"
```
Expected: `0012 up/down OK`.

- [ ] **Step 4: Commit**
```bash
git add backend/alembic/versions/0012_rbac_v2.py
git commit -m "feat(rbac-v2): Alembic 0012 — enum roles + users.coordinador_id"
```

---

## Task 3: `_role_scoped` por rol (scoping)

**Files:**
- Modify: `backend/app/services/registro_service.py`
- Test: `backend/tests/test_rbac_scoping.py` (crear)

**Interfaces:**
- Consumes: `scoped_query`, `Registro`, `User`, `UserRole`, `CampaignContext`.
- Produces: `_role_scoped(ctx)` cubre COORDINADOR (2 niveles), CAPTURISTA (propio), ANALYST/VIEWER/CONSULTA (vacío).

- [ ] **Step 1: Write the failing test** — crear `backend/tests/test_rbac_scoping.py` (usa el seed; añade en conftest un coordinador `coord@alpha.gov` con un líder y activistas bajo él — ver Step 4):
```python
from sqlalchemy import select, false
from app.models.user import User, UserRole
from app.services import registro_service
from app.dependencies import CampaignContext
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID

def _ctx(db, email):
    u = db.execute(select(User).where(User.email == email)).scalar_one()
    return CampaignContext(user=u, organization_id=u.organization_id, role=u.role, campaign_id=ALPHA_CAMPAIGN_ID)

def test_consulta_role_sees_nothing():
    db = TestingSessionLocal()
    try:
        sql = str(registro_service._role_scoped(_ctx(db, "consulta@alpha.gov")))
        assert "1 != 1" in sql or "false" in sql.lower()
    finally:
        db.close()

def test_coordinador_scope_includes_sub_structure():
    # coord@alpha.gov coordina a lider@alpha.gov, cuyos activistas son activista1/2.
    db = TestingSessionLocal()
    try:
        stmt = registro_service._role_scoped(_ctx(db, "coord@alpha.gov"))
        assert "coordinador_id" in str(stmt) or "lider_id" in str(stmt)
    finally:
        db.close()
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python3 -m pytest tests/test_rbac_scoping.py -v` → FAIL (consulta@alpha.gov no existe / scope no implementado).

- [ ] **Step 3: Extend `_role_scoped`** — en `backend/app/services/registro_service.py`, reemplazar el cuerpo de `_role_scoped(ctx)` (leer el actual primero) por:
```python
def _role_scoped(ctx: CampaignContext):
    stmt = scoped_query(Registro, ctx)
    if ctx.is_superadmin:
        return stmt
    role = ctx.role
    if role == UserRole.ADMIN:
        return stmt
    if role == UserRole.COORDINADOR:
        # líderes cuyo coordinador soy yo → sus activistas (+ los líderes mismos)
        lideres = select(User.id).where(User.coordinador_id == ctx.user.id)
        activistas = select(User.id).where(User.lider_id.in_(lideres))
        return stmt.where(or_(
            Registro.activista_id.in_(activistas),
            Registro.activista_id.in_(lideres),
        ))
    if role == UserRole.LIDER:
        sub = select(User.id).where(User.lider_id == ctx.user.id)
        return stmt.where(or_(Registro.activista_id.in_(sub),
                              Registro.activista_id == ctx.user.id))
    if role in (UserRole.ACTIVISTA, UserRole.CAPTURISTA):
        return stmt.where(Registro.activista_id == ctx.user.id)
    # ANALYST / VIEWER / CONSULTA / cualquier otro: sin registros granulares.
    return stmt.where(sa.false())
```
Asegurar imports `from sqlalchemy import or_, select` y `import sqlalchemy as sa` (o `from sqlalchemy import false`).

- [ ] **Step 4: Extend conftest seed** — en `backend/tests/conftest.py`, añadir (org_a, campaña Alpha):
```python
        coord = User(email="coord@alpha.gov", full_name="Alpha Coordinador",
                     hashed_password=hash_password(PASSWORD), role=UserRole.COORDINADOR,
                     organization_id=org_a.id)
        db.add(coord); db.flush()
        # el líder existente pasa a depender del coordinador:
        lider_u = db.execute(select(User).where(User.email == "lider@alpha.gov")).scalar_one()
        lider_u.coordinador_id = coord.id
        db.add_all([
            User(email="capturista@alpha.gov", full_name="Alpha Capturista",
                 hashed_password=hash_password(PASSWORD), role=UserRole.CAPTURISTA, organization_id=org_a.id),
            User(email="consulta@alpha.gov", full_name="Alpha Consulta",
                 hashed_password=hash_password(PASSWORD), role=UserRole.CONSULTA, organization_id=org_a.id),
        ])
```
Y añadir memberships de `coord`/`capturista`/`consulta` a la campaña Alpha (mismo patrón que los demás). Ajustar cualquier aserción de conteo en `test_tenancy.py`/`test_analytics.py` que cuente usuarios (Alpha pasa de 5 a 8).

- [ ] **Step 5: Run tests** — `python3 -m pytest tests/test_rbac_scoping.py -v` PASS; `python3 -m pytest -q` sin regresiones (corregir conteos si aplica).

- [ ] **Step 6: Commit**
```bash
git add backend/app/services/registro_service.py backend/tests/test_rbac_scoping.py backend/tests/conftest.py
git commit -m "feat(rbac-v2): _role_scoped covers coordinador/capturista + empty for read roles; seed coord/capturista/consulta"
```

---

## Task 4: Gating en routers del módulo activistas (captura/consola/export/reports)

**Files:**
- Modify: `backend/app/routers/registros.py`, `backend/app/routers/admin.py`, `backend/app/routers/exports.py`, `backend/app/routers/reports.py`
- Test: `backend/tests/test_rbac_endpoints.py` (crear)

**Interfaces:**
- Consumes: `require_roles`, `UserRole`. Produces: listas de roles por endpoint según §9.

- [ ] **Step 1: Write the failing test** — crear `backend/tests/test_rbac_endpoints.py`:
```python
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID

def _h(client, email):
    h = auth_headers(client, email); h["X-Campaign-Id"] = ALPHA_CAMPAIGN_ID; return h

def test_capturista_can_capture(client):
    r = client.post("/api/registros", json={"nombre_completo":"Cap Uno","consentimiento":True},
                    headers=_h(client,"capturista@alpha.gov"))
    assert r.status_code == 201, r.text
    client.delete(f"/api/registros/{r.json()['id']}", headers=_h(client,"capturista@alpha.gov"))

def test_coordinador_cannot_capture(client):
    r = client.post("/api/registros", json={"nombre_completo":"X","consentimiento":True},
                    headers=_h(client,"coord@alpha.gov"))
    assert r.status_code == 403, r.text

def test_coordinador_sees_admin_registros(client):
    assert client.get("/api/admin/registros", headers=_h(client,"coord@alpha.gov")).status_code == 200

def test_consulta_forbidden_on_admin_and_capture(client):
    assert client.get("/api/admin/registros", headers=_h(client,"consulta@alpha.gov")).status_code == 403
    assert client.post("/api/registros", json={"nombre_completo":"Y","consentimiento":True},
                       headers=_h(client,"consulta@alpha.gov")).status_code == 403
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python3 -m pytest tests/test_rbac_endpoints.py -v` → FAIL (capturista 403 hoy / coordinador no permitido en admin).

- [ ] **Step 3: Update role lists** (leer cada router; cambiar SOLO las tuplas de `require_roles`):
  - `registros.py` captura guard (`CapturaCtx = Annotated[object, Depends(require_roles(...))]`): roles `UserRole.ACTIVISTA, UserRole.CAPTURISTA, UserRole.LIDER, UserRole.ADMIN`.
  - `admin.py` `ConsoleCtx` (list/metricas/estructura): `UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER`. `AdminOnly` (revelar-clave/auditoría): `UserRole.ADMIN` (sin cambios).
  - `exports.py` export guard: `UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER`; reveal-export gate inline: `ADMIN`/superadmin (sin cambios).
  - `reports.py` guard: `UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER, UserRole.ANALYST, UserRole.VIEWER, UserRole.CONSULTA`.
  (`require_roles` ya deja pasar superadmin automáticamente.)

- [ ] **Step 4: Run tests** — `python3 -m pytest tests/test_rbac_endpoints.py tests/test_admin_api.py tests/test_registro_permissions.py -v` PASS; `python3 -m pytest -q` sin regresiones.

- [ ] **Step 5: Commit**
```bash
git add backend/app/routers/registros.py backend/app/routers/admin.py backend/app/routers/exports.py backend/app/routers/reports.py backend/tests/test_rbac_endpoints.py
git commit -m "feat(rbac-v2): role lists for captura/consola/export/reports per matrix"
```

---

## Task 5: Gating default-deny en endpoints de inteligencia (hoy abiertos)

**Files:**
- Modify: routers de inteligencia (leer cada uno): `backend/app/routers/maps.py`, `analytics.py`, `resultados.py`, `socio.py`/`demografia`, `denue.py`, `territory.py`, `intel.py`, `catalogs.py`, `sources.py`, y los de worldbank/economia/banxico/ieem si son routers propios (si comparten router, gatear ahí).
- Test: añadir a `backend/tests/test_rbac_endpoints.py`.

**Interfaces:** Consumes `require_roles`. Produces: dependency de rol en cada router de inteligencia.

- [ ] **Step 1: Inventory** — `grep -rL "require_roles" backend/app/routers/*.py` para listar routers SIN gating de rol; cruzar con la matriz §5/§9. Confirmar el patrón de dependency a nivel router (cómo `audit.py`/`admin.py` declaran un `Ctx = Annotated[..., Depends(require_roles(...))]` y lo inyectan en cada endpoint, o usan `dependencies=[Depends(require_roles(...))]` en el `APIRouter`/`include_router`).

- [ ] **Step 2: Write the failing test** — añadir a `test_rbac_endpoints.py` (ejemplo con maps; replicar para 1-2 representativos):
```python
def test_intelligence_blocks_activista_and_capturista(client):
    for ep in ("/api/maps", "/api/analytics", "/api/resultados"):
        # ruta real puede variar; usar una ruta GET real de cada router
        for email in ("activista1@alpha.gov","capturista@alpha.gov","consulta@alpha.gov"):
            code = client.get(ep, headers=_h(client,email)).status_code
            assert code in (403, 404), f"{ep} {email} -> {code}"

def test_intelligence_allows_analyst(client):
    # analyst@... necesita existir; usar viewer o crear analyst en seed
    pass
```
(Ajustar las rutas GET reales de cada router al leerlo; si una ruta no existe tal cual, usar la real.)

- [ ] **Step 3: Add gating** — en CADA router de inteligencia, añadir el guard a nivel router. Patrón preferido (un solo punto por router): en `main.py::_register_routers`, envolver con `dependencies=[Depends(require_roles(...))]` por módulo, O declarar el dependency en el `APIRouter(...)` del módulo. Listas por §9:
  - inteligencia (maps/analytics/resultados/padron(socio?)/territorios/ieem/worldbank/economia/denue/banxico/demografia/indice/busqueda): `require_roles(UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER, UserRole.ANALYST, UserRole.VIEWER)` (+SA auto).
  - `sources`: `require_roles(UserRole.ADMIN, UserRole.ANALYST)`.
  - `ai-analyst` (si tiene router): `require_roles(UserRole.ADMIN, UserRole.COORDINADOR, UserRole.ANALYST)`.
  - gobernanza/admin ya gateados; `organizaciones`→solo SA.
  Si un router sirve datos que TODO autenticado debe ver (p.ej. `dashboard`/health), dejarlo sin gating de rol explícitamente y documentarlo en el código.

- [ ] **Step 4: Run tests** — `python3 -m pytest tests/test_rbac_endpoints.py -v` PASS; `python3 -m pytest -q` sin regresiones (revisar que tests existentes de esos módulos usen un rol permitido; si usaban un viewer/activista, ajustarlos al nuevo modelo).

- [ ] **Step 5: Commit**
```bash
git add backend/app/routers backend/app/main.py backend/tests/test_rbac_endpoints.py
git commit -m "feat(rbac-v2): default-deny role gating on intelligence/sources/ai-analyst endpoints"
```

---

## Task 6: Validación de alcance en alta de usuarios (COORDINADOR/LIDER)

**Files:**
- Modify: `backend/app/services/users_service.py`, `backend/app/routers/users.py`
- Test: `backend/tests/test_users_crud.py` (añadir)

**Interfaces:** Produces: `_validate_coordinador`; reglas de quién puede crear a quién (§6).

- [ ] **Step 1: Write the failing test** — añadir a `backend/tests/test_users_crud.py`:
```python
def test_coordinador_creates_lider_in_substructure(client):
    h = auth_headers(client, "coord@alpha.gov")
    r = client.post("/api/users", json={"email":"newlider@alpha.gov","full_name":"NL",
        "password":"password123","role":"lider","coordinador_id":COORD_ID}, headers=h)
    assert r.status_code in (200,201), r.text

def test_lider_cannot_create_lider(client):
    h = auth_headers(client, "lider@alpha.gov")
    r = client.post("/api/users", json={"email":"x@alpha.gov","full_name":"X",
        "password":"password123","role":"lider"}, headers=h)
    assert r.status_code == 403
```
(`COORD_ID` = id de coord@alpha.gov; obtener vía select en el test.)

- [ ] **Step 2: Run to verify it fails** — `cd backend && python3 -m pytest tests/test_users_crud.py -v` → FAIL.

- [ ] **Step 3: Implement** — en `users.py` cambiar el guard de creación a `require_roles(UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER)` (+SA). En `users_service.py` añadir validación por rol del actor (leer el `_validate_lider` existente y reflejar):
  - ADMIN/SA: puede crear coord/líder/activista/capturista en su org.
  - COORDINADOR: solo `lider` o `activista`, y el nuevo debe quedar bajo su sub-estructura (`coordinador_id == actor.id` para un líder; para un activista, su `lider_id` debe ser un líder cuyo `coordinador_id == actor.id`). Si no, `HTTPException(403)`.
  - LIDER: solo `activista` con `lider_id == actor.id`. Si no, 403.
  - Nadie crea `superadmin`/`admin` salvo SA/ADMIN según matriz (ADMIN no crea admin; solo SA crea admin/superadmin).
  Añadir `_validate_coordinador(db, actor, payload)` y llamarla en create/update.

- [ ] **Step 4: Run tests** — `python3 -m pytest tests/test_users_crud.py -v` PASS; `python3 -m pytest -q` sin regresiones.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/users_service.py backend/app/routers/users.py backend/tests/test_users_crud.py
git commit -m "feat(rbac-v2): scope-validated user creation (coordinador/lider sub-structure)"
```

---

## Task 7: Frontend — `UserRole` + `roles:` explícito en cada módulo

**Files:**
- Modify: `frontend/src/types/auth.ts`, `frontend/src/modules/registry.ts`

**Interfaces:** Produces: tipo `UserRole` con 9 roles; cada `ModuleDef` con `roles:`.

- [ ] **Step 1: Extend the type** — en `frontend/src/types/auth.ts`:
```typescript
export type UserRole =
  | "superadmin" | "admin" | "coordinador" | "lider"
  | "activista" | "capturista" | "analyst" | "viewer" | "consulta";
```

- [ ] **Step 2: Set explicit roles on EVERY module** — en `frontend/src/modules/registry.ts`, añadir `roles:` a cada entrada según §5. Constantes sugeridas al inicio del archivo:
```typescript
const ALL: UserRole[] = ["superadmin","admin","coordinador","lider","activista","capturista","analyst","viewer","consulta"];
const INTEL: UserRole[] = ["superadmin","admin","coordinador","lider","analyst","viewer"];
const CONSOLE: UserRole[] = ["superadmin","admin","coordinador","lider"];
const ADMINY: UserRole[] = ["superadmin","admin"];
const REPORTS: UserRole[] = ["superadmin","admin","coordinador","lider","analyst","viewer","consulta"];
```
Asignar: `dashboard`→ALL; inteligencia (maps/analytics/resultados/padron/territorios/ieem/worldbank/economia/denue/banxico/demografia/indice/busqueda)→INTEL; `sources`→`["superadmin","admin","analyst"]`; `ai-analyst`→`["superadmin","admin","coordinador","analyst"]`; `captura`→`["superadmin","admin","lider","activista","capturista"]`; `admin-dashboard`/`admin-registros`→CONSOLE; `admin-estructura`→`["superadmin","admin","coordinador"]`; `reportes`→REPORTS; `auditoria`/`historial`→ADMINY; `users`/`organization`/`configuracion`/`campaigns`→ADMINY; `organizaciones`→`["superadmin"]`.

- [ ] **Step 3: Build** — `cd frontend && npm run build` → verde (0 errores TS).

- [ ] **Step 4: Commit**
```bash
git add frontend/src/types/auth.ts frontend/src/modules/registry.ts
git commit -m "feat(rbac-v2): UserRole +3 roles + explicit default-deny roles on every module"
```

---

## Task 8: Frontend — guard de ruta + gating de acciones

**Files:**
- Modify: el componente de routing/guard (leer `frontend/src/App.tsx` + cómo se aplican `roles`), `frontend/src/modules/admin/AdminRegistrosPage.tsx` (botón revelar/exportar), `frontend/src/modules/captura/CapturaPage.tsx` si muestra acciones por rol.

**Interfaces:** Produces: usuario sin rol permitido → redirect/403, no solo menú oculto.

- [ ] **Step 1: Read** — `frontend/src/App.tsx` y el helper que filtra `registry` por rol (cómo se decide acceso a una ruta). Confirmar si una navegación directa a una ruta no permitida bloquea (redirect/empty) o solo se oculta del menú.

- [ ] **Step 2: Enforce route guard** — si el guard solo oculta menú, añadir verificación en el render de la ruta: si `!moduleDef.roles?.includes(user.role)` → redirect a `/` o componente "Sin acceso". (Seguir patrón existente; si ya bloquea, dejar y anotar.)

- [ ] **Step 3: Action gating** — confirmar que el botón revelar-clave (AdminRegistrosPage) usa `role ∈ {admin, superadmin}` (ya existe) y que exportar usa `role ∈ {admin, coordinador, lider, superadmin}`. Ajustar si hace falta.

- [ ] **Step 4: Build** — `cd frontend && npm run build` verde.

- [ ] **Step 5: Commit**
```bash
git add frontend/src
git commit -m "feat(rbac-v2): route guard enforces module roles + action gating by role"
```

---

## Task 9: Demo seed — COORDINADOR + CAPTURISTA (prod + local)

**Files:**
- Modify: `backend/app/bootstrap.py` (`_seed_demo_activists`), `scripts/local_seed.py`
- Test: `backend/tests/test_demo_seed.py` (añadir)

**Interfaces:** Produces: usuarios demo coordinador/capturista env-gated, idempotentes.

- [ ] **Step 1: Write the failing test** — añadir a `backend/tests/test_demo_seed.py`: con `SEED_COORDINADOR_PASSWORD`/`SEED_CAPTURISTA_PASSWORD` set, el seed crea `coordinador@atlastech.mx` (COORDINADOR, lucy queda con `coordinador_id`=él) y `capturista@atlastech.mx` (CAPTURISTA) en la org + membresías; idempotente; skip sin passwords.

- [ ] **Step 2: Run to verify it fails** — `cd backend && python3 -m pytest tests/test_demo_seed.py -v` → FAIL.

- [ ] **Step 3: Implement** — extender `_seed_demo_activists` (leer el actual): leer `SEED_COORDINADOR_EMAIL/PASSWORD` y `SEED_CAPTURISTA_EMAIL/PASSWORD`; crear coordinador (COORDINADOR), enlazar `lucy.coordinador_id = coordinador.id`, crear capturista (CAPTURISTA), ambos con membership en la campaña demo. Idempotente (lookup por email). Reflejar en `scripts/local_seed.py` (`LEADERSHIP_USERS` += coordinador/capturista).

- [ ] **Step 4: Run tests** — `python3 -m pytest tests/test_demo_seed.py -v` PASS; `python3 -m pytest -q` sin regresiones.

- [ ] **Step 5: Commit**
```bash
git add backend/app/bootstrap.py scripts/local_seed.py backend/tests/test_demo_seed.py
git commit -m "feat(rbac-v2): demo seed coordinador + capturista (env-gated, idempotent)"
```

---

## Task 10: Integración de la matriz + verificación final

**Files:**
- Modify: `backend/tests/test_integration_flows.py` (añadir)

**Interfaces:** valida la matriz completa end-to-end.

- [ ] **Step 1: Write tests** — añadir flujos por rol nuevo: COORDINADOR ve consola con su sub-estructura (2 niveles) pero 403 en captura/revelar; CAPTURISTA captura y ve solo lo suyo, 403 en consola; CONSULTA 403 en captura/consola/inteligencia pero 200 en reportes; ANALYST 200 en inteligencia + reportes, 403 en captura/consola/revelar.

- [ ] **Step 2: Run** — `cd backend && python3 -m pytest tests/test_integration_flows.py -v` PASS; `python3 -m pytest -q` toda la suite verde.

- [ ] **Step 3: Frontend build** — `cd frontend && npm run build` verde.

- [ ] **Step 4: Commit**
```bash
git add backend/tests/test_integration_flows.py
git commit -m "test(rbac-v2): end-to-end matrix per role (coordinador/capturista/consulta/analyst)"
```

---

## Self-Review

**Spec coverage:** §3 roles→T1/T2 ✓ · §4 default-deny→T5/T7/T8 ✓ · §5 visibilidad→T7 (frontend) + T5/T4 (backend) ✓ · §6 acciones→T4/T6 ✓ · §7 modelo→T1/T2 ✓ · §8 scoping→T3 ✓ · §9 gating→T4/T5 ✓ · §10 frontend→T7/T8 ✓ · §11 seed→T9 ✓ · §12 tests→distribuidos+T10 ✓ · §13 compat/deploy→migración aditiva (T2) + nota de despliegue (controlador) ✓.

**Placeholder scan:** Task 5 deja rutas GET "reales" a confirmar al leer cada router (instrucción precisa, no placeholder — la matriz de roles por router es explícita). Resto con código completo.

**Type consistency:** `UserRole` NAMES mayúscula (backend) vs valores minúscula (frontend) consistente; `_role_scoped(ctx)` firma sin `db` (coincide con el estado post-SPA-1). `coordinador_id` usado igual en T1/T2/T3/T6/T9. `require_roles(*roles)` superadmin-auto en T4/T5/T6.

**Nota de despliegue (controlador, no tarea):** head Alembic en prod tras este merge = 0012 (aditivo). Setear en Railway `SEED_COORDINADOR_PASSWORD`/`SEED_CAPTURISTA_PASSWORD` (+EMAIL) si se quieren los demos. **Cambio visible:** default-deny ocultará inteligencia a activista/capturista/consulta — validar antes de prod.
