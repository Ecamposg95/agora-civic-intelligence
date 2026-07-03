# Territorio + Promovidos (San Mateo Atenco) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que el superadmin asigne un territorio (área) a un usuario, importar los Excel de promovidos a `Registro`, y mostrar una tabla de promovidos acotada al territorio y enriquecida con la matriz electoral 2024 por sección.

**Architecture:** Tres componentes sobre el spine existente. **A** (territorio): `User.area_id` + helper `scope_secciones`. **B** (electoral): modelo `SeccionElectoral` sembrado de un CSV del estudio. **C** (promovidos): CLI que parsea los XLSX → `Registro`, `GET /promovidos` que hace join a `SeccionElectoral` y filtra por territorio, y una página tabla. Todo se une porque el territorio de Lucy resuelve sus secciones y esas acotan la tabla.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 (Mapped) · Alembic · Pydantic v2 · openpyxl (ya instalado 3.1.5) · pytest (SQLite in-memory) · React + TypeScript + Vite + Tailwind · Vitest.

## Global Constraints

- Reglas Alembic (CLAUDE.md): DDL idempotente con guardas; SQLite-compatible; enum values MAYÚSCULAS (aquí no hay enums nuevos). Migración **aditiva**, `down_revision="0013"`, nueva revisión `"0014"`.
- Golden Rules: toda query de negocio filtra por `organization_id`/`campaign_id` (via `scoped_query`/`_role_scoped`); `organization_id`/`activista_id` en writes vienen del contexto, nunca del input; endpoints devuelven schemas Pydantic, nunca ORM crudo; RBAC en la capa API con `require_roles`; **la clave de elector nunca se loguea ni se expone en listas — solo `clave_masked`**.
- PII: el importador **nunca** loguea nombres/teléfonos/domicilios de promovidos (solo conteos). Los `docs/data/separados/*.xlsx` contienen PII y no se committean.
- Asignación de territorio: **solo superadmin** puede escribir (`PUT /users/{id}/territorio`).
- Consentimiento de import: `consentimiento=True`, `aviso_version="import-papel-2024"`, `activista_id=None`, un `AuditLog` `action="registro.import"` por lote.
- Idempotencia de import: `client_uuid = sha1(f"{archivo}|{hoja}|{fila}").hexdigest()[:32]`.
- Heurística de año 2 dígitos: `yy > 25 ⇒ 1900+yy`, `yy ≤ 25 ⇒ 2000+yy` (referencia 2026). Edad = 2026 − año. Además se preserva la fecha cruda `dd/mm/aaaa` en `observacion` con prefijo `"nac: "`.
- Nombre de la vista frontend: **"Promovidos"**.
- Tests backend: `cd backend && python3 -m pytest`. Frontend: `cd frontend && npm run build` + `npm run test`.

---

## File Structure

**Backend**
- `backend/app/models/user.py` — +`area_id` + relación `area`.
- `backend/app/models/seccion_electoral.py` — **crear** modelo `SeccionElectoral`.
- `backend/app/models/registro.py` — +`promotor`.
- `backend/alembic/versions/0014_territorio_promovidos.py` — **crear** migración aditiva.
- `backend/app/schemas/user.py` — `UserRead`/`PerfilRead`-adyacentes +area; `TerritorioAssign`.
- `backend/app/schemas/registro.py` — (perfil area vive en `PerfilRead` aquí).
- `backend/app/schemas/promovido.py` — **crear** `PromovidoRead`, `PromovidoList`.
- `backend/app/schemas/seccion_electoral.py` — **crear** `SeccionElectoralRead` (para tests/serialización interna).
- `backend/app/services/territory_service.py` — **crear** `assigned_area`, `scope_area_ids`, `scope_secciones`, `search_areas`.
- `backend/app/services/promovido_service.py` — **crear** `list_promovidos`.
- `backend/app/services/import_service.py` — **crear** `parse_workbook`, `import_rows`.
- `backend/app/seeds/__init__.py`, `backend/app/seeds/demo_territory.py` — **crear** seed idempotente.
- `backend/app/seeds/san_mateo_atenco_secciones_2024.csv` — **ya existe** (22 filas).
- `backend/app/routers/users.py` — +`PUT /users/{id}/territorio`.
- `backend/app/routers/territory.py` — +`GET /territory/search`.
- `backend/app/routers/promovidos.py` — **crear** `GET /promovidos`.
- `backend/app/routers/registros.py` — `/perfil` +area.
- `backend/app/main.py` — registrar router `promovidos`; llamar seed en lifespan (env-gated).
- `backend/scripts/import_promovidos.py` — **crear** CLI.
- `backend/tests/test_territorio.py`, `test_seccion_electoral.py`, `test_import_promovidos.py`, `test_promovidos_api.py` — **crear**.

**Frontend**
- `frontend/src/api/territory.ts` — search + assign.
- `frontend/src/api/promovidos.ts` — list.
- `frontend/src/modules/promovidos/PromovidosPage.tsx` — **crear** tabla.
- `frontend/src/modules/registry.ts` — módulo "Promovidos".
- `frontend/src/pages/UsersPage.tsx` (o equivalente) — selector de territorio (superadmin) + columna.
- Perfil (captura/perfil o dashboard) — muestra territorio / empty-state.

---

## Task 1: Modelos + migración 0014

**Files:**
- Modify: `backend/app/models/user.py`, `backend/app/models/registro.py`
- Create: `backend/app/models/seccion_electoral.py`
- Create: `backend/alembic/versions/0014_territorio_promovidos.py`
- Test: `backend/tests/test_territorio.py`

**Interfaces:**
- Produces: `User.area_id: Optional[str]`, `User.area` (relationship); `Registro.promotor: Optional[str]`; `SeccionElectoral` con columnas `seccion, municipio, anio, lista_nominal, votos, participacion, coalicion, morena, margen, prioridad`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_territorio.py`:

```python
"""Territorio + promovidos — modelos, scope, asignación, tabla."""
from app.models.user import User
from app.models.registro import Registro
from app.models.seccion_electoral import SeccionElectoral


def test_models_have_new_columns():
    assert "area_id" in User.__table__.columns
    assert "promotor" in Registro.__table__.columns
    cols = set(SeccionElectoral.__table__.columns.keys())
    assert {"seccion", "municipio", "anio", "lista_nominal", "votos",
            "participacion", "coalicion", "morena", "margen", "prioridad"}.issubset(cols)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_territorio.py::test_models_have_new_columns -v`
Expected: FAIL — `ModuleNotFoundError: app.models.seccion_electoral` / columnas ausentes.

- [ ] **Step 3: Create the SeccionElectoral model**

Crear `backend/app/models/seccion_electoral.py`:

```python
"""SeccionElectoral — resultado electoral histórico por sección (reference data)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class SeccionElectoral(UUIDMixin, Base):
    __tablename__ = "seccion_electoral"
    __table_args__ = (
        UniqueConstraint("seccion", "anio", name="uq_seccion_electoral_seccion_anio"),
    )

    seccion: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    municipio: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    lista_nominal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    votos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    participacion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coalicion: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    morena: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    margen: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prioridad: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
```

- [ ] **Step 4: Add columns to User and Registro**

En `backend/app/models/user.py`, tras la columna `seccion` (línea ~68), añadir:

```python
    area_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("electoral_areas.id", ondelete="SET NULL"),
        index=True, nullable=True,
    )
```

y tras la relación `organization` (línea ~72) añadir:

```python
    area: Mapped[Optional["ElectoralArea"]] = relationship(
        "ElectoralArea", lazy="joined", foreign_keys=[area_id]
    )
```

Asegurar el import `from app.models.electoral_area import ElectoralArea` bajo el bloque `if TYPE_CHECKING:` del archivo (o import directo si ya se importan modelos ahí; usa `TYPE_CHECKING` para evitar ciclo y referencia string en el relationship). Verifica que `ForeignKey` esté importado de sqlalchemy (ya lo está para `lider_id`).

En `backend/app/models/registro.py`, tras `observacion` (de Captura v2), añadir:

```python
    promotor: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_territorio.py::test_models_have_new_columns -v`
Expected: PASS.

- [ ] **Step 6: Write the migration**

Crear `backend/alembic/versions/0014_territorio_promovidos.py` (aditiva, idempotente, SQLite-safe; el FK de `users.area_id` se añade como columna simple — la constraint DB solo en PostgreSQL, guardada):

```python
"""Territorio + promovidos: users.area_id, seccion_electoral, registros.promotor.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # users.area_id (plain indexed column; FK constraint only on PG)
    if not _has_column("users", "area_id"):
        op.add_column("users", sa.Column("area_id", sa.String(length=36), nullable=True))
        op.create_index("ix_users_area_id", "users", ["area_id"])
        if is_pg:
            op.create_foreign_key(
                "fk_users_area_id", "users", "electoral_areas",
                ["area_id"], ["id"], ondelete="SET NULL",
            )

    # registros.promotor
    if not _has_column("registros", "promotor"):
        op.add_column("registros", sa.Column("promotor", sa.String(length=160), nullable=True))

    # seccion_electoral
    if not _has_table("seccion_electoral"):
        op.create_table(
            "seccion_electoral",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("seccion", sa.String(length=20), nullable=False),
            sa.Column("municipio", sa.String(length=120), nullable=True),
            sa.Column("anio", sa.Integer(), nullable=False),
            sa.Column("lista_nominal", sa.Integer(), nullable=True),
            sa.Column("votos", sa.Integer(), nullable=True),
            sa.Column("participacion", sa.Float(), nullable=True),
            sa.Column("coalicion", sa.Integer(), nullable=True),
            sa.Column("morena", sa.Integer(), nullable=True),
            sa.Column("margen", sa.Integer(), nullable=True),
            sa.Column("prioridad", sa.String(length=30), nullable=True),
            sa.UniqueConstraint("seccion", "anio", name="uq_seccion_electoral_seccion_anio"),
        )
        op.create_index("ix_seccion_electoral_seccion", "seccion_electoral", ["seccion"])


def downgrade() -> None:
    if _has_table("seccion_electoral"):
        op.drop_table("seccion_electoral")
    if _has_column("registros", "promotor"):
        op.drop_column("registros", "promotor")
    if _has_column("users", "area_id"):
        if op.get_bind().dialect.name == "postgresql":
            op.drop_constraint("fk_users_area_id", "users", type_="foreignkey")
        op.drop_index("ix_users_area_id", table_name="users")
        op.drop_column("users", "area_id")
```

- [ ] **Step 7: Verify head + full suite**

Run: `cd backend && python3 -m alembic heads`
Expected: `0014 (head)`.

Run: `cd backend && python3 -m pytest -q`
Expected: PASS (baseline + nuevo test).

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/user.py backend/app/models/registro.py backend/app/models/seccion_electoral.py backend/alembic/versions/0014_territorio_promovidos.py backend/tests/test_territorio.py
git commit -m "feat(territorio): modelos + migración 0014 — area_id, seccion_electoral, promotor"
```

---

## Task 2: territory_service (alcance territorial)

**Files:**
- Create: `backend/app/services/territory_service.py`
- Test: `backend/tests/test_territorio.py`

**Interfaces:**
- Consumes: `User.area_id`, `ElectoralArea` (level, id, code, municipio_id, estado_id, parent_id).
- Produces:
  - `assigned_area(db, user) -> ElectoralArea | None`
  - `scope_area_ids(db, user) -> set[str]` (área + descendientes)
  - `scope_secciones(db, user) -> set[str]` (códigos de secciones en alcance)
  - `search_areas(db, org_id, q, level, limit=20) -> list[ElectoralArea]`

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_territorio.py`. Usa fixtures del conftest + crea áreas de prueba vía la sesión de test. Primero, añade un helper que siembre un municipio + 2 secciones y asigna a un usuario:

```python
from sqlalchemy import select
from tests.conftest import TestingSessionLocal
from app.models.electoral_area import ElectoralArea, AreaLevel
from app.services import territory_service


def _seed_muni_with_secciones():
    db = TestingSessionLocal()
    try:
        muni = ElectoralArea(name="San Mateo Atenco", code="15076",
                             level=AreaLevel.MUNICIPIO, organization_id=None)
        db.add(muni); db.flush()
        s1 = ElectoralArea(name="Sección 4121", code="4121", level=AreaLevel.SECCION,
                           organization_id=None, municipio_id=muni.id, parent_id=muni.id)
        s2 = ElectoralArea(name="Sección 4122", code="4122", level=AreaLevel.SECCION,
                           organization_id=None, municipio_id=muni.id, parent_id=muni.id)
        db.add_all([s1, s2]); db.commit()
        return muni.id
    finally:
        db.close()


def test_scope_secciones_for_municipio():
    from app.models.user import User
    muni_id = _seed_muni_with_secciones()
    db = TestingSessionLocal()
    try:
        user = db.execute(select(User).where(User.email == "coord@alpha.gov")).scalar_one()
        user.area_id = muni_id
        db.commit()
        secs = territory_service.scope_secciones(db, user)
        assert secs == {"4121", "4122"}
    finally:
        db.close()


def test_scope_secciones_empty_without_area():
    from app.models.user import User
    db = TestingSessionLocal()
    try:
        user = db.execute(select(User).where(User.email == "lider@alpha.gov")).scalar_one()
        user.area_id = None
        db.commit()
        assert territory_service.scope_secciones(db, user) == set()
    finally:
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_territorio.py -k scope_secciones -v`
Expected: FAIL — `ModuleNotFoundError: app.services.territory_service`.

- [ ] **Step 3: Implement the service**

Crear `backend/app/services/territory_service.py`:

```python
"""Territory scope helpers — resolve a user's assigned area and its secciones."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.electoral_area import AreaLevel, ElectoralArea
from app.models.user import User


def assigned_area(db: Session, user: User) -> Optional[ElectoralArea]:
    if not user.area_id:
        return None
    return db.execute(
        select(ElectoralArea).where(ElectoralArea.id == user.area_id)
    ).scalar_one_or_none()


def scope_area_ids(db: Session, user: User) -> set[str]:
    area = assigned_area(db, user)
    if area is None:
        return set()
    ids = {area.id}
    # descendants via denormalized FKs (estado_id / municipio_id / parent_id)
    stmt = select(ElectoralArea.id).where(
        or_(
            ElectoralArea.estado_id == area.id,
            ElectoralArea.municipio_id == area.id,
            ElectoralArea.parent_id == area.id,
        )
    )
    ids.update(i for (i,) in db.execute(stmt).all())
    return ids


def scope_secciones(db: Session, user: User) -> set[str]:
    area = assigned_area(db, user)
    if area is None:
        return set()
    if area.level == AreaLevel.SECCION:
        return {area.code} if area.code else set()
    stmt = select(ElectoralArea.code).where(ElectoralArea.level == AreaLevel.SECCION)
    if area.level == AreaLevel.MUNICIPIO:
        stmt = stmt.where(ElectoralArea.municipio_id == area.id)
    elif area.level == AreaLevel.ESTADO:
        stmt = stmt.where(ElectoralArea.estado_id == area.id)
    else:
        stmt = stmt.where(ElectoralArea.parent_id == area.id)
    return {c for (c,) in db.execute(stmt).all() if c}


def search_areas(
    db: Session, org_id: Optional[str], q: Optional[str],
    level: Optional[str], limit: int = 20,
) -> list[ElectoralArea]:
    stmt = select(ElectoralArea).where(
        ElectoralArea.deleted_at.is_(None),
        or_(ElectoralArea.organization_id.is_(None),
            ElectoralArea.organization_id == org_id),
    )
    if q:
        stmt = stmt.where(ElectoralArea.name.ilike(f"%{q}%"))
    if level:
        stmt = stmt.where(ElectoralArea.level == level)
    return list(db.execute(stmt.limit(limit)).scalars().all())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_territorio.py -k scope_secciones -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/territory_service.py backend/tests/test_territorio.py
git commit -m "feat(territorio): territory_service — assigned_area/scope_area_ids/scope_secciones/search_areas"
```

---

## Task 3: Seed — San Mateo Atenco (área + 22 secciones) + SeccionElectoral

**Files:**
- Create: `backend/app/seeds/__init__.py`, `backend/app/seeds/demo_territory.py`
- Modify: `backend/app/main.py` (llamada al seed en lifespan, env-gated)
- Test: `backend/tests/test_seccion_electoral.py`

**Interfaces:**
- Consumes: `SeccionElectoral`, `ElectoralArea`, el CSV `san_mateo_atenco_secciones_2024.csv`.
- Produces: `seed_demo_territory(db) -> None` (idempotente): crea el municipio + 22 secciones (`ElectoralArea`) y 22 filas `SeccionElectoral`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_seccion_electoral.py`:

```python
"""Seed de territorio demo — San Mateo Atenco + matriz seccional 2024."""
from sqlalchemy import func, select

from app.models.electoral_area import AreaLevel, ElectoralArea
from app.models.seccion_electoral import SeccionElectoral
from app.seeds.demo_territory import seed_demo_territory
from tests.conftest import TestingSessionLocal


def test_seed_creates_municipio_secciones_and_matrix():
    db = TestingSessionLocal()
    try:
        seed_demo_territory(db)
        muni = db.execute(select(ElectoralArea).where(
            ElectoralArea.code == "15076")).scalar_one()
        assert muni.level == AreaLevel.MUNICIPIO
        n_sec = db.execute(select(func.count()).select_from(ElectoralArea).where(
            ElectoralArea.level == AreaLevel.SECCION,
            ElectoralArea.municipio_id == muni.id)).scalar_one()
        assert n_sec == 22
        n_fact = db.execute(select(func.count()).select_from(SeccionElectoral).where(
            SeccionElectoral.anio == 2024)).scalar_one()
        assert n_fact == 22
        row = db.execute(select(SeccionElectoral).where(
            SeccionElectoral.seccion == "4121")).scalar_one()
        assert row.margen == -115 and row.prioridad == "COMPETITIVA"
    finally:
        db.close()


def test_seed_is_idempotent():
    db = TestingSessionLocal()
    try:
        seed_demo_territory(db)
        seed_demo_territory(db)
        n = db.execute(select(func.count()).select_from(SeccionElectoral)).scalar_one()
        assert n == 22
        n_area = db.execute(select(func.count()).select_from(ElectoralArea).where(
            ElectoralArea.code == "15076")).scalar_one()
        assert n_area == 1
    finally:
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_seccion_electoral.py -v`
Expected: FAIL — `ModuleNotFoundError: app.seeds.demo_territory`.

- [ ] **Step 3: Implement the seed**

Crear `backend/app/seeds/__init__.py` vacío. Crear `backend/app/seeds/demo_territory.py`:

```python
"""Idempotent demo-territory seed: San Mateo Atenco municipio + 22 secciones
(ElectoralArea) and the 2024 electoral matrix (SeccionElectoral) from the study CSV."""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.electoral_area import AreaLevel, ElectoralArea
from app.models.seccion_electoral import SeccionElectoral

_CSV = Path(__file__).parent / "san_mateo_atenco_secciones_2024.csv"
_MUNI_CODE = "15076"
_MUNI_NAME = "San Mateo Atenco"
_ANIO = 2024


def seed_demo_territory(db: Session) -> None:
    # 1. Municipio (idempotent by code)
    muni = db.execute(
        select(ElectoralArea).where(ElectoralArea.code == _MUNI_CODE)
    ).scalar_one_or_none()
    if muni is None:
        muni = ElectoralArea(
            name=_MUNI_NAME, code=_MUNI_CODE,
            level=AreaLevel.MUNICIPIO, organization_id=None,
        )
        db.add(muni)
        db.flush()

    rows = list(csv.DictReader(_CSV.open(encoding="utf-8")))

    # 2. Secciones (ElectoralArea) + matrix (SeccionElectoral)
    for r in rows:
        code = r["seccion"]
        sec_area = db.execute(
            select(ElectoralArea).where(
                ElectoralArea.code == code,
                ElectoralArea.level == AreaLevel.SECCION,
            )
        ).scalar_one_or_none()
        if sec_area is None:
            db.add(ElectoralArea(
                name=f"Sección {code}", code=code, level=AreaLevel.SECCION,
                organization_id=None, municipio_id=muni.id, parent_id=muni.id,
            ))
        fact = db.execute(
            select(SeccionElectoral).where(
                SeccionElectoral.seccion == code, SeccionElectoral.anio == _ANIO)
        ).scalar_one_or_none()
        if fact is None:
            db.add(SeccionElectoral(
                seccion=code, municipio=_MUNI_NAME, anio=_ANIO,
                lista_nominal=int(r["lista_nominal"]), votos=int(r["votos"]),
                participacion=float(r["participacion"]),
                coalicion=int(r["coalicion"]), morena=int(r["morena"]),
                margen=int(r["margen"]), prioridad=r["prioridad"],
            ))
    db.commit()
```

- [ ] **Step 4: Wire the seed into startup (env-gated)**

En `backend/app/main.py`, localizar el lifespan (donde se llama `ensure_crypto_ready` y el demo-seed de usuarios). Tras el seed de usuarios existente, añadir (importa `os` y la función):

```python
    if os.getenv("SEED_DEMO_TERRITORY", "").lower() == "true":
        from app.seeds.demo_territory import seed_demo_territory
        from app.database import SessionLocal
        _db = SessionLocal()
        try:
            seed_demo_territory(_db)
        finally:
            _db.close()
```

(Usa el mismo patrón/importe de sesión que el seed de usuarios ya usa en `main.py`; si ese seed usa un context manager distinto, réplica ese estilo.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_seccion_electoral.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/seeds/__init__.py backend/app/seeds/demo_territory.py backend/app/main.py backend/tests/test_seccion_electoral.py
git commit -m "feat(territorio): seed idempotente San Mateo Atenco (municipio + 22 secciones + matriz 2024)"
```

---

## Task 4: API de asignación de territorio + perfil

**Files:**
- Modify: `backend/app/schemas/user.py`, `backend/app/routers/users.py`, `backend/app/routers/territory.py`, `backend/app/routers/registros.py`, `backend/app/schemas/registro.py`
- Test: `backend/tests/test_territorio.py`

**Interfaces:**
- Consumes: `territory_service.search_areas`, `User.area`.
- Produces:
  - `PUT /users/{id}/territorio` body `TerritorioAssign{area_id: str | None}` — superadmin only.
  - `GET /territory/search?q=&level=` → `[{id,name,level,code}]`.
  - `UserRead` +`area_id, area_nombre, area_nivel`.
  - `GET /perfil` → `PerfilRead` +`area: {id,nombre,nivel} | None`.

- [ ] **Step 1: Write the failing tests**

Añadir a `backend/tests/test_territorio.py`:

```python
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID


def _superhdr(client):
    return auth_headers(client, "super@atlas.gov")


def test_only_superadmin_assigns_territory(client):
    from app.models.user import User
    muni_id = _seed_muni_with_secciones()
    coord_id = _user_id(client, "coord@alpha.gov")

    # admin (not superadmin) → 403
    r = client.put(f"/api/users/{coord_id}/territorio",
                   json={"area_id": muni_id}, headers=auth_headers(client, "admin@alpha.gov"))
    assert r.status_code == 403, r.text

    # superadmin → 200 and area shows on the user
    r = client.put(f"/api/users/{coord_id}/territorio",
                   json={"area_id": muni_id}, headers=_superhdr(client))
    assert r.status_code == 200, r.text
    assert r.json()["area_nombre"] == "San Mateo Atenco"

    # nonexistent area → 404
    r = client.put(f"/api/users/{coord_id}/territorio",
                   json={"area_id": "does-not-exist"}, headers=_superhdr(client))
    assert r.status_code == 404


def test_territory_search_and_perfil(client):
    _seed_muni_with_secciones()
    r = client.get("/api/territory/search", params={"q": "San Mateo"},
                   headers=auth_headers(client, "admin@alpha.gov"))
    assert r.status_code == 200
    assert any(a["name"] == "San Mateo Atenco" for a in r.json())


def _user_id(client, email):
    from sqlalchemy import select
    from app.models.user import User
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        return db.execute(select(User.id).where(User.email == email)).scalar_one()
    finally:
        db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_territorio.py -k "superadmin_assigns or search_and_perfil" -v`
Expected: FAIL — 404 (endpoints inexistentes).

- [ ] **Step 3: Add schemas**

En `backend/app/schemas/user.py`: en `UserRead` añadir:

```python
    area_id: str | None = None
    area_nombre: str | None = None
    area_nivel: str | None = None
```

y una clase nueva:

```python
class TerritorioAssign(BaseModel):
    area_id: str | None = None
```

`UserRead.model_validate(user)` no llenará `area_nombre`/`area_nivel` automáticamente (viven en `user.area`). En el router se setean como atributos transitorios antes de validar (ver Step 5) o se construye el dict. Para mantener `from_attributes`, añade una propiedad en el modelo `User`:

En `backend/app/models/user.py` añade (tras la relación `area`):

```python
    @property
    def area_nombre(self) -> Optional[str]:
        return self.area.name if self.area else None

    @property
    def area_nivel(self) -> Optional[str]:
        return self.area.level.value if self.area else None
```

Así `UserRead.model_validate` (from_attributes) los lee directo.

En `backend/app/schemas/registro.py`, en `PerfilRead` añadir:

```python
    area: Optional[dict] = None   # {"id","nombre","nivel"} | None
```

- [ ] **Step 4: Add the territory search endpoint**

En `backend/app/routers/territory.py`, añadir (reusa `_INTEL_READ`? No — search es admin/superadmin). Añade un guard e import:

```python
from app.services import territory_service

_AREA_MANAGE = Depends(require_roles(UserRole.ADMIN))  # superadmin auto-passes


@router.get("/search")
def search(
    db: DbSession, ctx: Tenant, _perm: object = _AREA_MANAGE,
    q: Optional[str] = None, level: Optional[str] = None,
):
    areas = territory_service.search_areas(db, ctx.organization_id, q, level)
    return [{"id": a.id, "name": a.name, "level": a.level.value, "code": a.code} for a in areas]
```

- [ ] **Step 5: Add the assignment endpoint (superadmin-only)**

En `backend/app/routers/users.py`, añadir (import `TerritorioAssign`, `ElectoralArea`, `UserRole`, `select`):

```python
SuperadminCtx = Annotated[TenantContext, Depends(require_roles())]  # only superadmin passes


@router.put("/{user_id}/territorio", response_model=UserRead, summary="Assign territory (superadmin)")
def assign_territory(
    user_id: str, payload: TerritorioAssign, db: DbSession, ctx: SuperadminCtx
) -> UserRead:
    user = users_service.get_user(db, ctx, user_id)
    if payload.area_id is not None:
        area = db.execute(
            select(ElectoralArea).where(ElectoralArea.id == payload.area_id)
        ).scalar_one_or_none()
        if area is None:
            raise HTTPException(status_code=404, detail="Área no encontrada")
    user.area_id = payload.area_id
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
```

> `require_roles()` con cero roles → solo superadmin pasa (superadmin auto-pass en `require_roles`). Verifica ese comportamiento en `app/dependencies.py`; si `require_roles()` sin roles no lo garantiza, usa un guard explícito que compruebe `ctx.is_superadmin` y devuelva 403 si no.

- [ ] **Step 6: Enrich /perfil with area**

En `backend/app/routers/registros.py`, en el endpoint `perfil`, construir el area dict:

```python
    area = None
    if ctx.user.area_id and ctx.user.area:
        area = {"id": ctx.user.area.id, "nombre": ctx.user.area.name,
                "nivel": ctx.user.area.level.value}
```

y pasar `area=area` al `PerfilRead(...)`.

- [ ] **Step 7: Run tests + full suite**

Run: `cd backend && python3 -m pytest tests/test_territorio.py -v`
Expected: PASS.

Run: `cd backend && python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/user.py backend/app/schemas/registro.py backend/app/routers/users.py backend/app/routers/territory.py backend/app/routers/registros.py backend/app/models/user.py backend/tests/test_territorio.py
git commit -m "feat(territorio): PUT /users/{id}/territorio (superadmin) + /territory/search + perfil.area"
```

---

## Task 5: import_service (parseo de XLSX)

**Files:**
- Create: `backend/app/services/import_service.py`
- Test: `backend/tests/test_import_promovidos.py`

**Interfaces:**
- Produces:
  - `parse_workbook(path: str) -> list[dict]` — devuelve filas de promovido con claves: `nombre_completo, direccion, colonia, seccion, telefono, edad, observacion, promotor, estructura, _sheet, _row`.
  - `_edad_from(dia, mes, anio, ref_year=2026) -> int | None`.

- [ ] **Step 1: Write the failing test (build a fixture xlsx in-test)**

Crear `backend/tests/test_import_promovidos.py`:

```python
"""Parser de Excel de promovidos + import idempotente."""
import openpyxl

from app.services import import_service


def _make_xlsx(path, header_row=1):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ALAN URIEL RAMIREZ"
    r = header_row
    ws.cell(r, 1, "N.P."); ws.cell(r, 2, "PRIMER APELLIDO"); ws.cell(r, 3, "SEGUNDO APELLIDO")
    ws.cell(r, 4, "NOMBRE"); ws.cell(r, 5, "FECHA DE NACIMIENTO"); ws.cell(r, 8, "DOMICILIO")
    ws.cell(r, 12, "TELÉFONO CON WHATSAPP")
    ws.cell(r+1, 5, "DIA"); ws.cell(r+1, 6, "MES"); ws.cell(r+1, 7, "AÑO")
    ws.cell(r+1, 8, "CALLE"); ws.cell(r+1, 9, "#"); ws.cell(r+1, 10, "BARRIO/COLONIA")
    ws.cell(r+1, 11, "SECCIÓN")
    # data rows
    ws.cell(r+2, 1, 1); ws.cell(r+2, 2, "LEÓN"); ws.cell(r+2, 3, "ALCARAZ"); ws.cell(r+2, 4, "PEDRO")
    ws.cell(r+2, 5, 2); ws.cell(r+2, 6, 3); ws.cell(r+2, 7, 1988)
    ws.cell(r+2, 8, "C. MADERO"); ws.cell(r+2, 9, 506); ws.cell(r+2, 10, "BO. SAN FRANCISCO")
    ws.cell(r+2, 11, 4132); ws.cell(r+2, 12, "7226127261")
    # 2-digit year row
    ws.cell(r+3, 1, 2); ws.cell(r+3, 2, "GONZALEZ"); ws.cell(r+3, 3, "DAVILA"); ws.cell(r+3, 4, "ALBERTO")
    ws.cell(r+3, 5, 3); ws.cell(r+3, 6, 6); ws.cell(r+3, 7, 71)
    ws.cell(r+3, 11, 4130); ws.cell(r+3, 12, "7223478883")
    # empty row (only N.P.)
    ws.cell(r+4, 1, 3)
    wb.save(path)


def test_parse_maps_columns_and_edad(tmp_path):
    p = tmp_path / "ACTIVISMO CULTURA_Mayus.xlsx"
    _make_xlsx(str(p), header_row=1)
    rows = import_service.parse_workbook(str(p))
    assert len(rows) == 2  # empty row skipped
    r0 = rows[0]
    assert r0["nombre_completo"] == "PEDRO LEÓN ALCARAZ"
    assert r0["seccion"] == "4132"
    assert r0["telefono"] == "7226127261"
    assert r0["edad"] == 2026 - 1988
    assert r0["promotor"] == "ALAN URIEL RAMIREZ"
    assert r0["estructura"] == "ACTIVISMO CULTURA"
    assert r0["observacion"].startswith("nac: ")
    assert rows[1]["edad"] == 2026 - 1971  # 2-digit year 71 → 1971


def test_parse_header_on_row_3(tmp_path):
    p = tmp_path / "EMANUEL_Mayus.xlsx"
    _make_xlsx(str(p), header_row=3)
    rows = import_service.parse_workbook(str(p))
    assert len(rows) == 2 and rows[0]["seccion"] == "4132"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_import_promovidos.py -k parse -v`
Expected: FAIL — `ModuleNotFoundError: app.services.import_service`.

- [ ] **Step 3: Implement the parser**

Crear `backend/app/services/import_service.py`:

```python
"""Promovidos importer: parse messy multi-sheet XLSX into Registro-ready dicts."""
from __future__ import annotations

import os
import re
from typing import Optional

import openpyxl

_GENERIC_SHEETS = {"C1", "A", "HOJA1", "HOJA 1", "SHEET1"}


def _clean(v) -> str:
    return re.sub(r"\s+", " ", str(v).strip()) if v is not None else ""


def _edad_from(dia, mes, anio, ref_year: int = 2026) -> Optional[int]:
    try:
        y = int(float(anio))
    except (TypeError, ValueError):
        return None
    if y < 100:  # 2-digit year
        y = 1900 + y if y > 25 else 2000 + y
    if not (1900 <= y <= ref_year):
        return None
    return ref_year - y


def _find_header_row(ws) -> Optional[int]:
    for row in ws.iter_rows(min_row=1, max_row=8):
        joined = " ".join(_clean(c.value).upper() for c in row)
        if "PRIMER APELLIDO" in joined and "NOMBRE" in joined:
            return row[0].row
    return None


def _file_label(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"_Mayus$", "", base, flags=re.IGNORECASE).strip()


def parse_workbook(path: str) -> list[dict]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    estructura = _file_label(path)
    out: list[dict] = []
    for ws in wb.worksheets:
        hdr = _find_header_row(ws)
        if hdr is None:
            continue
        promotor = _clean(ws.title)
        if promotor.upper() in _GENERIC_SHEETS:
            promotor = estructura
        # columns are fixed by the standard template (see spec §5):
        # 2 ap1, 3 ap2, 4 nombre, 5 dia, 6 mes, 7 anio, 8 calle, 9 num,
        # 10 colonia, 11 seccion, 12 telefono
        for row in ws.iter_rows(min_row=hdr + 2, values_only=True):
            row = list(row) + [None] * (12 - len(row))
            ap1, ap2, nombre = _clean(row[1]), _clean(row[2]), _clean(row[3])
            if not (ap1 or ap2 or nombre):
                continue  # empty / spacer row
            nombre_completo = _clean(f"{nombre} {ap1} {ap2}")
            calle, num = _clean(row[7]), _clean(row[8])
            direccion = _clean(f"{calle} {num}") or None
            seccion = _clean(row[10]) or None
            tel = re.sub(r"\D", "", _clean(row[11])) or None
            dia, mes, anio = row[4], row[5], row[6]
            edad = _edad_from(dia, mes, anio)
            nac = "/".join(_clean(x) for x in (dia, mes, anio) if _clean(x))
            observacion = f"nac: {nac}" if nac else None
            out.append({
                "nombre_completo": nombre_completo,
                "direccion": direccion,
                "colonia": _clean(row[9]) or None,
                "seccion": seccion,
                "telefono": tel,
                "edad": edad,
                "observacion": observacion,
                "promotor": promotor,
                "estructura": estructura,
                "_sheet": ws.title,
                "_row": None,  # row index attached by caller for client_uuid
            })
    wb.close()
    return out
```

> Nota: `read_only=True` no da índice de fila fiable en `values_only`; el `client_uuid` se construye en Task 6 con un contador estable por (hoja, orden). Ajusta `_row` allí.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_import_promovidos.py -k parse -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_service.py backend/tests/test_import_promovidos.py
git commit -m "feat(promovidos): import_service.parse_workbook — parser tolerante de XLSX"
```

---

## Task 6: import_rows + CLI (idempotente, audit por lote)

**Files:**
- Modify: `backend/app/services/import_service.py`
- Create: `backend/scripts/import_promovidos.py`
- Test: `backend/tests/test_import_promovidos.py`

**Interfaces:**
- Consumes: `parse_workbook`, `Registro`, `AuditLog`/`record_audit`.
- Produces: `import_rows(db, *, organization_id, campaign_id, path) -> dict{leidas,importadas,duplicadas}` — idempotente por `client_uuid`, un audit por lote.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_import_promovidos.py`:

```python
from sqlalchemy import func, select
from app.models.registro import Registro
from app.models.audit_log import AuditLog
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID


def test_import_rows_idempotent_and_audited(tmp_path):
    p = tmp_path / "ACTIVISMO CULTURA_Mayus.xlsx"
    _make_xlsx(str(p), header_row=1)
    db = TestingSessionLocal()
    try:
        org_id = db.execute(select(Registro.organization_id).limit(1)).scalar()  # may be None
        # use the Alpha org id from a seeded user instead:
        from app.models.user import User
        org_id = db.execute(select(User.organization_id).where(
            User.email == "coord@alpha.gov")).scalar_one()

        res1 = import_service.import_rows(db, organization_id=org_id,
                                          campaign_id=ALPHA_CAMPAIGN_ID, path=str(p))
        assert res1["importadas"] == 2
        n1 = db.execute(select(func.count()).select_from(Registro).where(
            Registro.promotor == "ALAN URIEL RAMIREZ")).scalar_one()
        assert n1 == 2

        # re-run → no duplicates
        res2 = import_service.import_rows(db, organization_id=org_id,
                                          campaign_id=ALPHA_CAMPAIGN_ID, path=str(p))
        assert res2["importadas"] == 0 and res2["duplicadas"] == 2
        n2 = db.execute(select(func.count()).select_from(Registro).where(
            Registro.promotor == "ALAN URIEL RAMIREZ")).scalar_one()
        assert n2 == 2

        # one batch-audit row per import call
        n_audit = db.execute(select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "registro.import")).scalar_one()
        assert n_audit >= 1
    finally:
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_import_promovidos.py -k idempotent -v`
Expected: FAIL — `import_service.import_rows` no existe.

- [ ] **Step 3: Implement import_rows**

Añadir a `backend/app/services/import_service.py` (imports arriba):

```python
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.registro import Registro
from app.services.audit_service import record_audit


def _client_uuid(path: str, sheet: str, idx: int) -> str:
    key = f"{os.path.basename(path)}|{sheet}|{idx}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:32]


def import_rows(db: Session, *, organization_id: str, campaign_id: str, path: str) -> dict:
    rows = parse_workbook(path)
    leidas = len(rows)
    importadas = 0
    duplicadas = 0
    # stable per-sheet counter for deterministic client_uuid
    per_sheet: dict[str, int] = {}
    for r in rows:
        sheet = r["_sheet"]
        idx = per_sheet.get(sheet, 0)
        per_sheet[sheet] = idx + 1
        cuid = _client_uuid(path, sheet, idx)
        exists = db.execute(
            select(Registro.id).where(
                Registro.campaign_id == campaign_id,
                Registro.client_uuid == cuid,
            )
        ).scalar_one_or_none()
        if exists:
            duplicadas += 1
            continue
        db.add(Registro(
            organization_id=organization_id,
            campaign_id=campaign_id,
            activista_id=None,
            nombre_completo=r["nombre_completo"],
            seccion=r["seccion"],
            direccion=r["direccion"],
            colonia=r["colonia"],
            telefono=r["telefono"],
            edad=r["edad"],
            estructura=r["estructura"],
            promotor=r["promotor"],
            observacion=r["observacion"],
            consentimiento=True,
            aviso_version="import-papel-2024",
            client_uuid=cuid,
        ))
        importadas += 1
    record_audit(
        db, action="registro.import", actor_id=None,
        organization_id=organization_id, entity_type="registro_batch",
        entity_id=os.path.basename(path),
    )
    db.commit()
    return {"leidas": leidas, "importadas": importadas, "duplicadas": duplicadas}
```

> Verifica la firma de `record_audit` (en `app/services/audit_service.py`) y ajusta los kwargs a los que acepta (p.ej. si `actor_id` no admite `None`, usa un marcador como `"import-cli"`). **No** incluyas nombres/teléfonos en el audit.

- [ ] **Step 4: Create the CLI**

Crear `backend/scripts/import_promovidos.py` (patrón de `scripts/purge_registros.py`):

```python
"""CLI: importar promovidos desde XLSX a Registro. Uso:

  python3 scripts/import_promovidos.py --campaign <campaign_id> --dir docs/data/separados [--dry-run]

Nunca imprime PII (solo conteos por archivo).
"""
import argparse
import glob
import os
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models.campaign import Campaign
from app.services import import_service


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        camp = db.execute(select(Campaign).where(Campaign.id == args.campaign)).scalar_one_or_none()
        if camp is None:
            print(f"campaign {args.campaign} not found", file=sys.stderr)
            return 2
        org_id = camp.organization_id
        files = sorted(glob.glob(os.path.join(args.dir, "*.xlsx")))
        total = {"leidas": 0, "importadas": 0, "duplicadas": 0}
        for f in files:
            if args.dry_run:
                rows = import_service.parse_workbook(f)
                print(f"{os.path.basename(f)}: {len(rows)} filas (dry-run)")
                continue
            res = import_service.import_rows(
                db, organization_id=org_id, campaign_id=args.campaign, path=f)
            for k in total:
                total[k] += res[k]
            print(f"{os.path.basename(f)}: {res}")
        print(f"TOTAL: {total}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_import_promovidos.py -v`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/import_service.py backend/scripts/import_promovidos.py backend/tests/test_import_promovidos.py
git commit -m "feat(promovidos): import_rows idempotente + CLI import_promovidos (audit por lote)"
```

---

## Task 7: promovido_service + GET /promovidos

**Files:**
- Create: `backend/app/services/promovido_service.py`, `backend/app/schemas/promovido.py`, `backend/app/routers/promovidos.py`
- Modify: `backend/app/main.py` (registrar router)
- Test: `backend/tests/test_promovidos_api.py`

**Interfaces:**
- Consumes: `registro_service._role_scoped`, `territory_service.scope_secciones`, `SeccionElectoral`.
- Produces: `GET /promovidos` → `PromovidoList{items: [PromovidoRead], total, limit, offset, has_territory}`. `PromovidoRead` = campos de registro + `promotor, participacion, margen, prioridad`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_promovidos_api.py`:

```python
"""GET /promovidos — scope territorial + enriquecimiento electoral."""
from sqlalchemy import select
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID, TestingSessionLocal
from app.models.electoral_area import AreaLevel, ElectoralArea
from app.models.seccion_electoral import SeccionElectoral
from app.models.registro import Registro
from app.models.user import User


def _h(client, email):
    h = auth_headers(client, email)
    h["X-Campaign-Id"] = ALPHA_CAMPAIGN_ID
    return h


def _setup_territory_and_promovido():
    db = TestingSessionLocal()
    try:
        muni = ElectoralArea(name="San Mateo Atenco", code="15076",
                             level=AreaLevel.MUNICIPIO, organization_id=None)
        db.add(muni); db.flush()
        db.add(ElectoralArea(name="Sección 4121", code="4121", level=AreaLevel.SECCION,
                             organization_id=None, municipio_id=muni.id, parent_id=muni.id))
        db.add(SeccionElectoral(seccion="4121", municipio="San Mateo Atenco", anio=2024,
                                participacion=66.9, margen=-115, prioridad="COMPETITIVA"))
        coord = db.execute(select(User).where(User.email == "coord@alpha.gov")).scalar_one()
        coord.area_id = muni.id
        db.add(Registro(organization_id=coord.organization_id, campaign_id=ALPHA_CAMPAIGN_ID,
                        activista_id=None, nombre_completo="Promovido Uno", seccion="4121",
                        promotor="ALAN", consentimiento=True, client_uuid="prom-1"))
        # a promovido OUTSIDE her territory (should be filtered out)
        db.add(Registro(organization_id=coord.organization_id, campaign_id=ALPHA_CAMPAIGN_ID,
                        activista_id=None, nombre_completo="Fuera", seccion="9999",
                        promotor="ALAN", consentimiento=True, client_uuid="prom-2"))
        db.commit()
    finally:
        db.close()


def test_promovidos_scoped_and_enriched(client):
    _setup_territory_and_promovido()
    r = client.get("/api/promovidos", headers=_h(client, "coord@alpha.gov"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_territory"] is True
    names = [i["nombre_completo"] for i in body["items"]]
    assert "Promovido Uno" in names and "Fuera" not in names  # territory filter
    row = next(i for i in body["items"] if i["nombre_completo"] == "Promovido Uno")
    assert row["prioridad"] == "COMPETITIVA" and row["margen"] == -115
    assert "clave_elector" not in row  # Golden Rule #9


def test_promovidos_empty_without_territory(client):
    db = TestingSessionLocal()
    try:
        lider = db.execute(select(User).where(User.email == "lider@alpha.gov")).scalar_one()
        lider.area_id = None
        db.commit()
    finally:
        db.close()
    r = client.get("/api/promovidos", headers=_h(client, "lider@alpha.gov"))
    assert r.status_code == 200
    assert r.json()["has_territory"] is False
    assert r.json()["items"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_promovidos_api.py -v`
Expected: FAIL — 404 (`/promovidos` inexistente).

- [ ] **Step 3: Implement schema + service**

Crear `backend/app/schemas/promovido.py`:

```python
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PromovidoRead(BaseModel):
    id: str
    nombre_completo: str
    seccion: Optional[str] = None
    colonia: Optional[str] = None
    telefono: Optional[str] = None
    edad: Optional[int] = None
    estructura: Optional[str] = None
    promotor: Optional[str] = None
    clave_masked: Optional[str] = None
    # electoral context (from SeccionElectoral, may be null)
    participacion: Optional[float] = None
    margen: Optional[int] = None
    prioridad: Optional[str] = None


class PromovidoList(BaseModel):
    items: list[PromovidoRead]
    total: int
    limit: int
    offset: int
    has_territory: bool
```

Crear `backend/app/services/promovido_service.py`:

```python
"""Promovidos listing — role+territory scoped, enriched with electoral context."""
from __future__ import annotations

from typing import Optional

import sqlalchemy as sa
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.dependencies import CampaignContext
from app.models.registro import Registro
from app.models.seccion_electoral import SeccionElectoral
from app.services import territory_service
from app.services.registro_service import _role_scoped


def list_promovidos(
    db: Session, ctx: CampaignContext, *, seccion: Optional[str], promotor: Optional[str],
    prioridad: Optional[str], q: Optional[str], limit: int, offset: int,
) -> tuple[list[Registro], int, bool]:
    secciones = territory_service.scope_secciones(db, ctx.user)
    has_territory = ctx.is_superadmin or bool(secciones)

    stmt = _role_scoped(ctx)
    if not ctx.is_superadmin:
        if not secciones:
            stmt = stmt.where(sa.false())
        else:
            stmt = stmt.where(Registro.seccion.in_(secciones))
    if seccion:
        stmt = stmt.where(Registro.seccion == seccion)
    if promotor:
        stmt = stmt.where(Registro.promotor.ilike(f"%{promotor}%"))
    if q:
        stmt = stmt.where(Registro.nombre_completo.ilike(f"%{q}%"))

    # prioridad filter needs the electoral join
    if prioridad:
        pr = select(SeccionElectoral.seccion).where(
            SeccionElectoral.prioridad == prioridad, SeccionElectoral.anio == 2024)
        stmt = stmt.where(Registro.seccion.in_(pr))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(
        stmt.order_by(Registro.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all())

    # enrich with electoral context (single query)
    codes = {r.seccion for r in rows if r.seccion}
    facts = {}
    if codes:
        for f in db.execute(select(SeccionElectoral).where(
            SeccionElectoral.seccion.in_(codes), SeccionElectoral.anio == 2024)
        ).scalars():
            facts[f.seccion] = f
    for r in rows:
        f = facts.get(r.seccion)
        r.participacion = f.participacion if f else None
        r.margen = f.margen if f else None
        r.prioridad = f.prioridad if f else None
    return rows, total, has_territory
```

- [ ] **Step 4: Implement the router + register it**

Crear `backend/app/routers/promovidos.py`:

```python
"""GET /promovidos — role+territory scoped promovidos table with electoral context."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import CampaignCtx, DbSession, require_roles
from app.models.user import UserRole
from app.schemas.promovido import PromovidoList, PromovidoRead
from app.services import promovido_service

router = APIRouter(tags=["promovidos"])

_READ = Annotated[object, Depends(require_roles(
    UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER))]


@router.get("/promovidos", response_model=PromovidoList)
def list_promovidos(
    db: DbSession, ctx: CampaignCtx, _perm: _READ,
    seccion: Annotated[Optional[str], Query()] = None,
    promotor: Annotated[Optional[str], Query()] = None,
    prioridad: Annotated[Optional[str], Query()] = None,
    q: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PromovidoList:
    rows, total, has_territory = promovido_service.list_promovidos(
        db, ctx, seccion=seccion, promotor=promotor, prioridad=prioridad,
        q=q, limit=limit, offset=offset)
    return PromovidoList(
        items=[PromovidoRead.model_validate(r, from_attributes=True) for r in rows],
        total=total, limit=limit, offset=offset, has_territory=has_territory)
```

En `backend/app/main.py`, importar y registrar el router junto a los demás:

```python
from app.routers import promovidos
app.include_router(promovidos.router, prefix="/api")
```

(usa el mismo prefijo/patrón que los routers existentes como `registros`).

- [ ] **Step 5: Run tests + full suite**

Run: `cd backend && python3 -m pytest tests/test_promovidos_api.py -v`
Expected: PASS (2 tests).

Run: `cd backend && python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/promovido.py backend/app/services/promovido_service.py backend/app/routers/promovidos.py backend/app/main.py backend/tests/test_promovidos_api.py
git commit -m "feat(promovidos): GET /promovidos — scope territorial + contexto electoral por sección"
```

---

## Task 8: Frontend — página Promovidos + módulo

**Files:**
- Create: `frontend/src/api/promovidos.ts`, `frontend/src/modules/promovidos/PromovidosPage.tsx`
- Modify: `frontend/src/modules/registry.ts`

**Interfaces:**
- Consumes: `GET /promovidos` → `{items, total, limit, offset, has_territory}`.
- Produces: módulo `promovidos` en el registry; página tabla.

- [ ] **Step 1: Add the API client**

Crear `frontend/src/api/promovidos.ts`:

```typescript
import { apiClient } from "./client";

export interface Promovido {
  id: string;
  nombre_completo: string;
  seccion: string | null;
  colonia: string | null;
  telefono: string | null;
  edad: number | null;
  estructura: string | null;
  promotor: string | null;
  clave_masked: string | null;
  participacion: number | null;
  margen: number | null;
  prioridad: string | null;
}

export interface PromovidoList {
  items: Promovido[];
  total: number;
  limit: number;
  offset: number;
  has_territory: boolean;
}

export interface PromovidoFilters {
  seccion?: string;
  promotor?: string;
  prioridad?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export async function listPromovidos(f: PromovidoFilters = {}): Promise<PromovidoList> {
  const params: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== "") params[k] = v;
  const { data } = await apiClient.get<PromovidoList>("/promovidos", { params });
  return data;
}
```

- [ ] **Step 2: Build the Promovidos page**

Crear `frontend/src/modules/promovidos/PromovidosPage.tsx`. Usa los componentes existentes (`AppLayout`, `PageHeader`, `Card`, `DataState`, `useAsync`) siguiendo el patrón de `CapturaPage.tsx`. Tabla con columnas Nombre · Edad · Sección · Colonia · Teléfono · Promotor · Estructura · Part.% · Margen · Prioridad (badge por color). Empty-state cuando `!has_territory`. Contenedor `overflow-x-auto` para móvil.

```tsx
import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { DataState } from "@/components/ui/DataState";
import { useAsync } from "@/hooks/useAsync";
import { listPromovidos, type Promovido } from "@/api/promovidos";

const PRIORIDAD_CLASS: Record<string, string> = {
  DEFENDER_EXPANDIR: "bg-state-success/10 text-state-success",
  COMPETITIVA: "bg-state-warning/10 text-state-warning",
  RECUPERAR_OPOSICION: "bg-state-critical/10 text-state-critical",
  ALTA_PERSUADIBLE: "bg-accent/10 text-accent",
};

export function PromovidosPage() {
  const [q, setQ] = useState("");
  const state = useAsync(() => listPromovidos({ q }), [q]);
  const data = state.data;

  return (
    <AppLayout title="Promovidos" crumb="Ciudadanía">
      <PageHeader eyebrow="Ciudadanía" title="Tabla de" accent="Promovidos"
        subtitle="Ciudadanos promovidos en tu territorio, con contexto electoral por sección." />

      {data && !data.has_territory ? (
        <div className="card-premium px-5 py-12 text-center text-ink-muted">
          Pídele a tu administrador que te asigne un territorio.
        </div>
      ) : (
        <Card title="Promovidos" accentDot
          action={<input className="field-input h-8 w-48" placeholder="Buscar nombre…"
            value={q} onChange={(e) => setQ(e.target.value)} />}>
          <DataState loading={state.loading} error={state.error} onRetry={state.reload}
            isEmpty={!state.loading && !state.error && (data?.items.length ?? 0) === 0}
            emptyMessage="Sin promovidos…">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-ink-faint">
                    <th className="py-2 pr-3">Nombre</th><th className="pr-3">Edad</th>
                    <th className="pr-3">Sección</th><th className="pr-3">Colonia</th>
                    <th className="pr-3">Teléfono</th><th className="pr-3">Promotor</th>
                    <th className="pr-3">Part.</th><th className="pr-3">Margen</th>
                    <th className="pr-3">Prioridad</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data?.items.map((p: Promovido) => (
                    <tr key={p.id}>
                      <td className="py-2 pr-3 font-medium text-ink">{p.nombre_completo}</td>
                      <td className="pr-3">{p.edad ?? "—"}</td>
                      <td className="pr-3 font-mono">{p.seccion ?? "—"}</td>
                      <td className="pr-3">{p.colonia ?? "—"}</td>
                      <td className="pr-3">{p.telefono ?? "—"}</td>
                      <td className="pr-3">{p.promotor ?? "—"}</td>
                      <td className="pr-3">{p.participacion != null ? `${p.participacion}%` : "—"}</td>
                      <td className="pr-3 tabular-nums">{p.margen ?? "—"}</td>
                      <td className="pr-3">
                        {p.prioridad ? (
                          <span className={`pill ${PRIORIDAD_CLASS[p.prioridad] ?? ""}`}>
                            {p.prioridad.replace(/_/g, " ")}
                          </span>
                        ) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DataState>
        </Card>
      )}
    </AppLayout>
  );
}
```

- [ ] **Step 3: Register the module**

En `frontend/src/modules/registry.ts`: añadir el lazy import junto a los demás:

```typescript
const Promovidos = lazy(() =>
  import("@/modules/promovidos/PromovidosPage").then((m) => ({ default: m.PromovidosPage })),
);
```

y una entrada en `MODULES` en la sección "Ciudadanía" (roles = consola: superadmin/admin/coordinador/lider):

```typescript
  { key: "promovidos", path: "/promovidos", label: "Promovidos", section: "ciudadania", icon: VotersIcon, state: "active", element: Promovidos, roles: ["superadmin", "admin", "coordinador", "lider"] },
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: PASS.

Run: `cd frontend && npm run test`
Expected: PASS (sin regresión).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/promovidos.ts frontend/src/modules/promovidos/PromovidosPage.tsx frontend/src/modules/registry.ts
git commit -m "feat(promovidos): página tabla de promovidos + módulo en el registry"
```

---

## Task 9: Frontend — selector de territorio (Usuarios) + territorio en Perfil

**Files:**
- Create: `frontend/src/api/territory.ts`
- Modify: la página de Usuarios (`frontend/src/pages/UsersPage.tsx` o equivalente) y el Perfil (en `CapturaPage.tsx` o el dashboard donde se muestra `getPerfil`).

**Interfaces:**
- Consumes: `GET /territory/search`, `PUT /users/{id}/territorio`, `GET /perfil` (ahora con `area`).
- Produces: UI para que el superadmin busque y asigne un territorio; el perfil muestra el territorio o el empty-state.

- [ ] **Step 1: Add the territory API client**

Crear `frontend/src/api/territory.ts`:

```typescript
import { apiClient } from "./client";

export interface AreaHit { id: string; name: string; level: string; code: string | null; }

export async function searchAreas(q: string, level?: string): Promise<AreaHit[]> {
  const params: Record<string, string> = {};
  if (q) params.q = q;
  if (level) params.level = level;
  const { data } = await apiClient.get<AreaHit[]>("/territory/search", { params });
  return data;
}

export async function assignTerritory(userId: string, areaId: string | null): Promise<void> {
  await apiClient.put(`/users/${userId}/territorio`, { area_id: areaId });
}
```

- [ ] **Step 2: Add the territory selector in the Users page (superadmin only)**

Primero, localizar la página de Usuarios: `grep -rl "UsersPage\|/users" frontend/src/pages frontend/src/modules`. En la fila/edición de un usuario, añadir (visible solo si el usuario actual es `superadmin`, leído de `useAuthStore`) un buscador de área que llama `searchAreas(q)` y, al elegir, `assignTerritory(userId, areaId)` y refresca la lista. Mostrar el `area_nombre` del usuario en el listado. Sigue el patrón de estado/tabla existente de esa página (no introduzcas librerías nuevas). Muestra el territorio asignado como un `pill`.

Requisitos concretos:
- El control solo se renderiza si `authStore.user?.role === "superadmin"`.
- Input de búsqueda → lista de resultados (`AreaHit[]`) → al hacer click: `await assignTerritory(user.id, hit.id)` → recargar usuarios.
- Botón "Quitar" → `assignTerritory(user.id, null)`.
- La columna de la tabla muestra `user.area_nombre ?? "—"`.

- [ ] **Step 3: Show the territory in the profile**

En el componente que muestra el perfil (donde se usa `getPerfil` — hoy en `CapturaPage.tsx`; añade el mismo bloque en el dashboard si aplica), extender el tipo `Perfil` con `area?: { id: string; nombre: string; nivel: string } | null` y renderizar un chip "Territorio: {area.nombre}" cuando exista, o el aviso *"Pídele a tu administrador que te asigne un territorio."* cuando `area` sea null.

En `frontend/src/api/registros.ts`, añadir a la interfaz `Perfil`:

```typescript
  area: { id: string; nombre: string; nivel: string } | null;
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: PASS.

Run: `cd frontend && npm run test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/territory.ts frontend/src/api/registros.ts frontend/src/pages frontend/src/modules/captura/CapturaPage.tsx
git commit -m "feat(territorio): selector de territorio (superadmin) en Usuarios + territorio/empty-state en Perfil"
```

---

## Self-Review (autor del plan)

**Spec coverage:**
- §3 A territorio: `User.area_id` (T1), helper scope (T2), seed área (T3), API asignación+search+perfil (T4), UI (T9). ✓
- §4 B electoral: `SeccionElectoral` (T1), seed matriz (T3). ✓
- §5 C promovidos: `Registro.promotor` (T1), parser (T5), import_rows+CLI+idempotencia+audit (T6), `GET /promovidos`+enriquecimiento+scope (T7), tabla (T8). ✓
- §6 integración A↔C: scope_secciones consumido en promovido_service (T7). ✓
- §8 testing: cada task trae sus tests; Golden Rule #9 verificada en T7. ✓
- Consentimiento import / audit por lote / PII no logueada (§5): T6. ✓
- Migración aditiva idempotente 0014 (§7): T1. ✓

**Placeholder scan:** sin TBD/TODO; cada paso con código lleva el código. Dos notas de verificación explícitas (firma de `record_audit` en T6; comportamiento de `require_roles()` sin roles en T4) son verificaciones dirigidas, no placeholders — el implementador confirma y ajusta al patrón real del repo.

**Type consistency:** `scope_secciones` (T2) devuelve `set[str]` de códigos, consumido igual en T7. `PromovidoRead` (T7) campos == `Promovido` TS (T8). `TerritorioAssign{area_id}` (T4) == body de `assignTerritory` (T9). `client_uuid` sha1(archivo|hoja|idx) consistente entre import_rows (T6) y su test. `area_nombre`/`area_nivel` propiedades en User (T4) == columnas mostradas en Users (T9).
