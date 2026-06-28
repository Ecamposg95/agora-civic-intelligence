# SPA-1 · Núcleo de Captura de Activistas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar el núcleo de captura online de activistas (modelo `registros`, API CRUD con scope por rol, frontend desde la semilla) sobre un fundamento multitenant correcto que habilita la visibilidad cross-tenant del superadmin, con cifrado Fernet + consentimiento obligatorio desde el día 1.

**Architecture:** Módulo nuevo dentro de `agora-civic-intelligence` reutilizando el spine (Organization/Campaign/User, JWT, `scoped_query`, AuditLog, Alembic). Capas: `models/` (ORM) → `schemas/` (Pydantic v2) → `services/` (lógica + audit + cripto) → `routers/` (HTTP). Frontend React/TS con module registry. La clave de elector se cifra (Fernet, enfoque B: enmascarado por defecto, sin descifrado en SPA-1).

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · Alembic 1.14 · Pydantic v2 · `cryptography` (Fernet) · PyJWT · React 18 + TS + Vite + Tailwind + Zustand.

## Global Constraints

- **Spec de referencia:** `docs/superpowers/specs/2026-06-27-spa1-nucleo-captura-activistas-design.md`. Toda tarea hereda sus reglas.
- **Golden Rules (de `docs/architecture.md`):** queries de negocio filtran por `organization_id`; el `organization_id`/`campaign_id` de escrituras viene del contexto (JWT/base seleccionada), nunca del body; endpoints devuelven Pydantic, nunca ORM; RBAC en la capa API; operaciones sensibles emiten `AuditLog`; nada de secretos hardcodeados; listas paginadas `{items,total,limit,offset}`; errores con envelope `{ "error": { "message", "status" } }`.
- **Cifrado enfoque B:** ninguna respuesta de SPA-1 expone `clave_elector_enc` ni la clave en claro; solo `clave_masked`. No existe endpoint de revelar en SPA-1.
- **Consentimiento obligatorio:** alta/edición con `consentimiento != true` → `422`.
- **`FERNET_KEY`:** se lee de env; sin ella la app falla (no fallback a texto en claro). Nunca en el repo.
- **Migraciones:** patrones endurecidos (helpers `_table_exists`/`_index_exists`, enum por NOMBRES en mayúscula, dialect-safe PG/SQLite, sin `try/except` de control de flujo). Head actual: `0007` → nueva: `0008`.
- **Tests:** corren contra SQLite in-memory (`tests/conftest.py`). Suite completa debe quedar verde (sin regresiones). Frontend: `npm run build` verde.
- **Rama:** `feat/spa1-captura-activistas` (ya creada desde `main`).

---

## File Structure

**Backend — crear:**
- `backend/app/core/crypto.py` — Fernet encrypt/decrypt/mask + fail-fast.
- `backend/app/models/registro.py` — modelo `Registro`.
- `backend/app/schemas/registro.py` — schemas Pydantic.
- `backend/app/services/registro_service.py` — lógica CRUD + cripto + consent + idempotencia + audit + scope por rol.
- `backend/app/routers/registros.py` — endpoints `/registros` + `/perfil`.
- `backend/alembic/versions/0008_activistas.py` — migración.
- `backend/tests/test_crypto.py`, `tests/test_registros.py`, `tests/test_registro_permissions.py` — tests nuevos.

**Backend — modificar:**
- `backend/requirements.txt` — añadir `cryptography`.
- `backend/app/core/config.py` — añadir `FERNET_KEY`.
- `backend/app/models/user.py` — `UserRole` (+LIDER/+ACTIVISTA), `lider_id`, `seccion`.
- `backend/app/models/__init__.py` — registrar `Registro`.
- `backend/app/core/scoping.py` — bypass superadmin.
- `backend/app/dependencies.py` — `get_campaign_context` adopta org de la base para superadmin.
- `backend/app/services/auth_service.py` — login por teléfono o email.
- `backend/app/schemas/auth.py` — `LoginRequest.identifier`.
- `backend/app/routers/auth.py` — usar `identifier`.
- `backend/app/main.py` — registrar router `registros` + `ensure_crypto_ready()` en lifespan.
- `backend/tests/conftest.py` — env `FERNET_KEY`, tabla `registros`, seed (lider/activistas, superadmin, campaña Beta).

**Frontend — crear:**
- `frontend/src/api/registros.ts` — cliente API.
- `frontend/src/modules/captura/CapturaPage.tsx` — formulario adaptado de la semilla.

**Frontend — modificar:**
- `frontend/src/modules/registry.ts` — registrar módulo `captura`.
- `frontend/src/pages/LoginPage.tsx` — campo identificador (teléfono o email).

---

## Task 1: Cripto (Fernet) + config + dependencia

**Files:**
- Create: `backend/app/core/crypto.py`
- Create: `backend/tests/test_crypto.py`
- Modify: `backend/requirements.txt`, `backend/app/core/config.py`, `backend/tests/conftest.py`

**Interfaces:**
- Produces: `encrypt_clave(plain: str) -> bytes`, `decrypt_clave(ct: bytes) -> str`, `mask_clave(plain: str) -> str`, `ensure_crypto_ready() -> None`. `settings.FERNET_KEY: str`.

- [ ] **Step 1: Añadir dependencia**

En `backend/requirements.txt`, bajo la sección `# --- Security ---`, añadir:
```
cryptography==44.0.0
```
Instalar: `pip install cryptography==44.0.0`

- [ ] **Step 2: Añadir `FERNET_KEY` a config**

En `backend/app/core/config.py`, dentro de la sección `# --- Security ---` (tras `ACCESS_TOKEN_EXPIRE_MINUTES`), añadir:
```python
    # Fernet key for encrypting clave de elector at rest. No default: the app
    # must fail rather than store sensitive data in clear. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY: str = Field(default="")
```

- [ ] **Step 3: Set FERNET_KEY en conftest (antes de importar la app)**

En `backend/tests/conftest.py`, en la PRIMERA línea ejecutable (antes de cualquier `from app...`), añadir:
```python
import os
from cryptography.fernet import Fernet

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
```
(El `setdefault` antes de los imports de `app.*` garantiza que `settings` cacheado lo recoja.)

- [ ] **Step 4: Write the failing test**

Crear `backend/tests/test_crypto.py`:
```python
"""Tests for app.core.crypto (Fernet encryption of clave de elector)."""
import pytest

from app.core import crypto


def test_encrypt_decrypt_round_trip():
    ct = crypto.encrypt_clave("ABCD1234567890XYZ8")
    assert isinstance(ct, bytes)
    assert ct != b"ABCD1234567890XYZ8"
    assert crypto.decrypt_clave(ct) == "ABCD1234567890XYZ8"


def test_mask_clave_shows_last_four():
    assert crypto.mask_clave("ABCD1234567890XYZ8") == "****-XYZ8"


def test_mask_clave_short_value():
    assert crypto.mask_clave("12") == "****-12"


def test_encrypt_fails_without_key(monkeypatch):
    monkeypatch.setattr(crypto.settings, "FERNET_KEY", "")
    crypto._build_fernet.cache_clear()
    with pytest.raises(RuntimeError):
        crypto.encrypt_clave("ABCD1234567890XYZ8")
    crypto._build_fernet.cache_clear()  # restore for other tests
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd backend && pytest tests/test_crypto.py -v`
Expected: FAIL (ModuleNotFoundError: app.core.crypto)

- [ ] **Step 6: Write minimal implementation**

Crear `backend/app/core/crypto.py`:
```python
"""Encryption helpers for sensitive fields (clave de elector).

Enfoque B: the service stores ciphertext + a masked display value. Decryption
exists only for the SPA-2 reveal flow (with audit) — not used in SPA-1.
The app fails fast if FERNET_KEY is missing: never store PII in clear.
"""
from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings


@lru_cache(maxsize=1)
def _build_fernet() -> Fernet:
    key = settings.FERNET_KEY
    if not key:
        raise RuntimeError(
            "FERNET_KEY is not set. Refusing to handle clave de elector without "
            "encryption. Set FERNET_KEY in the environment."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def ensure_crypto_ready() -> None:
    """Validate the Fernet key at startup. Raises RuntimeError if misconfigured."""
    _build_fernet()


def encrypt_clave(plain: str) -> bytes:
    """Encrypt a clave de elector. Returns ciphertext bytes."""
    return _build_fernet().encrypt(plain.encode())


def decrypt_clave(ct: bytes) -> str:
    """Decrypt ciphertext back to the clave. SPA-2 reveal only."""
    return _build_fernet().decrypt(ct).decode()


def mask_clave(plain: str) -> str:
    """Return a masked display value, e.g. ``****-XYZ8``."""
    return f"****-{plain[-4:]}"
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && pytest tests/test_crypto.py -v`
Expected: PASS (4 passed)

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/app/core/config.py backend/app/core/crypto.py backend/tests/test_crypto.py backend/tests/conftest.py
git commit -m "feat(spa1): Fernet crypto util for clave de elector + FERNET_KEY config"
```

---

## Task 2: Modelo User — roles LIDER/ACTIVISTA + lider_id + seccion

**Files:**
- Modify: `backend/app/models/user.py`
- Test: `backend/tests/test_registros.py` (crear; primer test del modelo de usuario extendido)

**Interfaces:**
- Consumes: `UserRole` (existente).
- Produces: `UserRole.LIDER`, `UserRole.ACTIVISTA`; `User.lider_id: Optional[str]`; `User.seccion: Optional[str]`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_registros.py`:
```python
"""Tests for the activist capture core (User extensions, Registro model)."""
from app.models.user import User, UserRole


def test_user_role_has_lider_and_activista():
    assert UserRole.LIDER.value == "lider"
    assert UserRole.ACTIVISTA.value == "activista"


def test_user_has_lider_and_seccion_columns():
    cols = User.__table__.c
    assert "lider_id" in cols
    assert "seccion" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_registros.py -v`
Expected: FAIL (AttributeError: LIDER)

- [ ] **Step 3: Write minimal implementation**

En `backend/app/models/user.py`:

(a) Extender el enum (tras `VIEWER = "viewer"`):
```python
    LIDER = "lider"
    ACTIVISTA = "activista"
```

(b) Tras la columna `phone` (línea ~53), añadir:
```python
    # Activist-structure hierarchy: an activist points to its leader; a leader
    # has lider_id = NULL. Self-FK on users.
    lider_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    seccion: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_registros.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run full suite (no regressions)**

Run: `cd backend && pytest -q`
Expected: PASS (todos verdes — el enum nuevo no rompe nada existente).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/user.py backend/tests/test_registros.py
git commit -m "feat(spa1): User gains LIDER/ACTIVISTA roles, lider_id self-FK, seccion"
```

---

## Task 3: Modelo Registro + schemas + registro en metadata + seed de tests

**Files:**
- Create: `backend/app/models/registro.py`, `backend/app/schemas/registro.py`
- Modify: `backend/app/models/__init__.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_registros.py` (añadir)

**Interfaces:**
- Consumes: mixins `UUIDMixin/TenantMixin/CampaignMixin/AuditMixin`; `User`, `UserRole`.
- Produces: `Registro` (tabla `registros`); schemas `RegistroCreate`, `RegistroUpdate`, `RegistroRead`, `RegistroList`, `PerfilRead`. Seed de tests: usuarios `lider@alpha.gov`, `activista1@alpha.gov` (lider_id=lider, phone `5550000001`), `activista2@alpha.gov` (lider_id=lider), `super@atlas.gov` (SUPERADMIN, org NULL), `activista_beta@beta.gov`; campaña Beta `BETA_CAMPAIGN_ID`; memberships en sus campañas. Constante `BETA_CAMPAIGN_ID = "22222222-2222-2222-2222-222222222222"`.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_registros.py`:
```python
from datetime import datetime, timezone

from app.core import crypto
from app.models.registro import Registro
from tests.conftest import TestingSessionLocal, ALPHA_CAMPAIGN_ID


def test_registro_stores_clave_encrypted_not_plain():
    db = TestingSessionLocal()
    try:
        from app.models.organization import Organization
        org = db.query(Organization).filter_by(slug="alpha").one()
        reg = Registro(
            organization_id=org.id,
            campaign_id=ALPHA_CAMPAIGN_ID,
            activista_id="someone",
            nombre_completo="Juan Pérez",
            clave_elector_enc=crypto.encrypt_clave("ABCD1234567890XYZ8"),
            clave_masked=crypto.mask_clave("ABCD1234567890XYZ8"),
            consentimiento=True,
            consentimiento_at=datetime.now(timezone.utc),
            aviso_version="v1",
        )
        db.add(reg)
        db.commit()
        db.refresh(reg)
        assert reg.clave_masked == "****-XYZ8"
        assert b"ABCD1234567890XYZ8" not in bytes(reg.clave_elector_enc)
        assert crypto.decrypt_clave(bytes(reg.clave_elector_enc)) == "ABCD1234567890XYZ8"
    finally:
        db.query(Registro).delete()
        db.commit()
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_registros.py::test_registro_stores_clave_encrypted_not_plain -v`
Expected: FAIL (ModuleNotFoundError: app.models.registro)

- [ ] **Step 3: Crear el modelo**

Crear `backend/app/models/registro.py`:
```python
"""Registro — a person captured by an activist (tidy operational fact)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, LargeBinary, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import AuditMixin, CampaignMixin, TenantMixin, UUIDMixin


class Registro(UUIDMixin, TenantMixin, CampaignMixin, AuditMixin, Base):
    __tablename__ = "registros"
    __table_args__ = (
        Index("ix_registros_campaign_activista", "campaign_id", "activista_id"),
        Index("ix_registros_campaign_seccion", "campaign_id", "seccion"),
        UniqueConstraint("campaign_id", "client_uuid", name="uq_registros_campaign_client_uuid"),
    )

    activista_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=False
    )
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    seccion: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    colonia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    area: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    clave_elector_enc: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    clave_masked: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    consentimiento: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consentimiento_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    aviso_version: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    client_uuid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
```

- [ ] **Step 4: Registrar el modelo en metadata**

En `backend/app/models/__init__.py`: añadir el import `from app.models.registro import Registro` (orden alfabético, tras `organization`), y añadir `"Registro"` a `__all__`.

- [ ] **Step 5: Crear schemas**

Crear `backend/app/schemas/registro.py`:
```python
"""Registro API schemas (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole


def _validate_clave(v: Optional[str]) -> Optional[str]:
    if v is None or v == "":
        return None
    cleaned = v.strip().upper()
    if len(cleaned) != 18 or not cleaned.isalnum():
        raise ValueError("clave de elector must be 18 alphanumeric characters")
    return cleaned


class RegistroCreate(BaseModel):
    nombre_completo: str = Field(min_length=2, max_length=255)
    seccion: Optional[str] = Field(default=None, max_length=20)
    direccion: Optional[str] = Field(default=None, max_length=500)
    colonia: Optional[str] = Field(default=None, max_length=255)
    telefono: Optional[str] = Field(default=None, max_length=40)
    area: Optional[str] = Field(default=None, max_length=120)
    clave_elector: Optional[str] = Field(default=None)
    consentimiento: bool
    client_uuid: Optional[str] = Field(default=None, max_length=64)
    lat: Optional[float] = None
    lng: Optional[float] = None

    @field_validator("clave_elector")
    @classmethod
    def _clave(cls, v):
        return _validate_clave(v)


class RegistroUpdate(BaseModel):
    nombre_completo: Optional[str] = Field(default=None, min_length=2, max_length=255)
    seccion: Optional[str] = Field(default=None, max_length=20)
    direccion: Optional[str] = Field(default=None, max_length=500)
    colonia: Optional[str] = Field(default=None, max_length=255)
    telefono: Optional[str] = Field(default=None, max_length=40)
    area: Optional[str] = Field(default=None, max_length=120)
    clave_elector: Optional[str] = Field(default=None)
    consentimiento: Optional[bool] = None

    @field_validator("clave_elector")
    @classmethod
    def _clave(cls, v):
        return _validate_clave(v)


class RegistroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    campaign_id: str
    activista_id: str
    nombre_completo: str
    seccion: Optional[str]
    direccion: Optional[str]
    colonia: Optional[str]
    telefono: Optional[str]
    area: Optional[str]
    clave_masked: Optional[str]
    consentimiento: bool
    consentimiento_at: Optional[datetime]
    created_at: datetime


class RegistroList(BaseModel):
    items: list[RegistroRead]
    total: int
    limit: int
    offset: int


class PerfilRead(BaseModel):
    id: str
    full_name: str
    role: UserRole
    seccion: Optional[str]
    lider_id: Optional[str]
    lider_nombre: Optional[str]
    organization_id: Optional[str]
```

- [ ] **Step 6: Extender conftest (tabla + seed)**

En `backend/tests/conftest.py`:

(a) Importar el modelo: `from app.models.registro import Registro` (junto a los otros imports de modelos).

(b) Añadir `Registro.__table__` a la lista `tables=[...]` de `Base.metadata.create_all`.

(c) Añadir la constante junto a `ALPHA_CAMPAIGN_ID`:
```python
BETA_CAMPAIGN_ID = "22222222-2222-2222-2222-222222222222"
```

(d) En `seed_data`, tras crear los usuarios alpha/beta existentes y antes del `db.commit()` que los persiste, añadir el líder/activistas/superadmin (necesitan `db.flush()` para obtener el id del líder):
```python
        lider = User(
            email="lider@alpha.gov", full_name="Alpha Líder",
            hashed_password=hash_password(PASSWORD), role=UserRole.LIDER,
            organization_id=org_a.id, seccion="0001",
        )
        db.add(lider)
        db.flush()
        db.add_all([
            User(email="activista1@alpha.gov", full_name="Alpha Activista 1",
                 hashed_password=hash_password(PASSWORD), role=UserRole.ACTIVISTA,
                 organization_id=org_a.id, lider_id=lider.id, phone="5550000001", seccion="0001"),
            User(email="activista2@alpha.gov", full_name="Alpha Activista 2",
                 hashed_password=hash_password(PASSWORD), role=UserRole.ACTIVISTA,
                 organization_id=org_a.id, lider_id=lider.id, seccion="0002"),
            User(email="super@atlas.gov", full_name="Platform Superadmin",
                 hashed_password=hash_password(PASSWORD), role=UserRole.SUPERADMIN,
                 organization_id=None),
            User(email="activista_beta@beta.gov", full_name="Beta Activista",
                 hashed_password=hash_password(PASSWORD), role=UserRole.ACTIVISTA,
                 organization_id=org_b.id, seccion="9001"),
        ])
```

(e) Tras crear el `camp` Alpha y su membership, añadir la campaña Beta + memberships de los nuevos usuarios:
```python
        beta_camp = Campaign(id=BETA_CAMPAIGN_ID, name="Beta 2027", cycle=2027, organization_id=org_b.id)
        db.add(beta_camp)
        db.flush()
        for email in ("lider@alpha.gov", "activista1@alpha.gov", "activista2@alpha.gov"):
            u = db.execute(select(User).where(User.email == email)).scalar_one()
            db.add(CampaignMembership(user_id=u.id, campaign_id=camp.id, role=u.role))
        beta_act = db.execute(select(User).where(User.email == "activista_beta@beta.gov")).scalar_one()
        db.add(CampaignMembership(user_id=beta_act.id, campaign_id=beta_camp.id, role=beta_act.role))
```

- [ ] **Step 7: Run tests**

Run: `cd backend && pytest tests/test_registros.py -v`
Expected: PASS (modelo + cifrado verificado). Y `pytest -q` sin regresiones.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/registro.py backend/app/schemas/registro.py backend/app/models/__init__.py backend/tests/conftest.py backend/tests/test_registros.py
git commit -m "feat(spa1): Registro model + schemas + test seed (lider/activistas/superadmin/beta)"
```

---

## Task 4: Migración Alembic 0008

**Files:**
- Create: `backend/alembic/versions/0008_activistas.py`

**Interfaces:**
- Consumes: head `0007` (`down_revision`). Modelos de Task 2/3.
- Produces: tabla `registros`; columnas `users.lider_id`, `users.seccion`; valores enum `LIDER`/`ACTIVISTA`.

- [ ] **Step 1: Inspeccionar la última migración como plantilla**

Leer `backend/alembic/versions/0007_tidy_facts.py` para copiar los helpers `_table_exists`/`_index_exists`, el patrón dialect-safe y el manejo de enums por NOMBRE.

- [ ] **Step 2: Escribir la migración**

Crear `backend/alembic/versions/0008_activistas.py`:
```python
"""SPA-1 activistas: registros table + user lider_id/seccion + roles.

Revision ID: 0008
Revises: 0007
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def _index_exists(table: str, index: str) -> bool:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table):
        return False
    return any(ix["name"] == index for ix in sa.inspect(bind).get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # 1. Extend the user_role enum (PG only; SQLite stores VARCHAR).
    if is_pg:
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'LIDER'")
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'ACTIVISTA'")

    # 2. users.lider_id + users.seccion.
    user_cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "lider_id" not in user_cols:
        op.add_column("users", sa.Column("lider_id", sa.String(length=36), nullable=True))
        op.create_foreign_key(
            "fk_users_lider_id", "users", "users", ["lider_id"], ["id"], ondelete="SET NULL"
        )
        op.create_index("ix_users_lider_id", "users", ["lider_id"])
    if "seccion" not in user_cols:
        op.add_column("users", sa.Column("seccion", sa.String(length=20), nullable=True))

    # 3. registros table.
    if not _table_exists("registros"):
        op.create_table(
            "registros",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36),
                      sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("campaign_id", sa.String(length=36),
                      sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("activista_id", sa.String(length=36),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
            sa.Column("nombre_completo", sa.String(length=255), nullable=False),
            sa.Column("seccion", sa.String(length=20), nullable=True),
            sa.Column("direccion", sa.String(length=500), nullable=True),
            sa.Column("colonia", sa.String(length=255), nullable=True),
            sa.Column("telefono", sa.String(length=40), nullable=True),
            sa.Column("area", sa.String(length=120), nullable=True),
            sa.Column("clave_elector_enc", sa.LargeBinary(), nullable=True),
            sa.Column("clave_masked", sa.String(length=20), nullable=True),
            sa.Column("consentimiento", sa.Boolean(), nullable=False),
            sa.Column("consentimiento_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("aviso_version", sa.String(length=40), nullable=True),
            sa.Column("client_uuid", sa.String(length=64), nullable=True),
            sa.Column("lat", sa.Float(), nullable=True),
            sa.Column("lng", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("updated_by", sa.String(length=36), nullable=True),
            sa.UniqueConstraint("campaign_id", "client_uuid", name="uq_registros_campaign_client_uuid"),
        )
    if not _index_exists("registros", "ix_registros_campaign_activista"):
        op.create_index("ix_registros_campaign_activista", "registros", ["campaign_id", "activista_id"])
    if not _index_exists("registros", "ix_registros_campaign_seccion"):
        op.create_index("ix_registros_campaign_seccion", "registros", ["campaign_id", "seccion"])
    if not _index_exists("registros", "ix_registros_organization_id"):
        op.create_index("ix_registros_organization_id", "registros", ["organization_id"])
    if not _index_exists("registros", "ix_registros_campaign_id"):
        op.create_index("ix_registros_campaign_id", "registros", ["campaign_id"])
    if not _index_exists("registros", "ix_registros_activista_id"):
        op.create_index("ix_registros_activista_id", "registros", ["activista_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists("registros"):
        op.drop_table("registros")
    user_cols = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "seccion" in user_cols:
        op.drop_column("users", "seccion")
    if "lider_id" in user_cols:
        if bind.dialect.name == "postgresql":
            op.drop_constraint("fk_users_lider_id", "users", type_="foreignkey")
        op.drop_index("ix_users_lider_id", table_name="users")
        op.drop_column("users", "lider_id")
    # Enum values are not removed (consistent with prior migrations).
```

> Nota sobre enums PG: el modelo usa `Enum(UserRole, name="user_role")`, que persiste los **valores** (`"lider"`, `"activista"`), no los nombres. Verificar contra `0001`/`0003` cómo se materializaron los valores existentes (`SUPERADMIN`→`'superadmin'` valor, o nombre). Replicar **exactamente** ese criterio para `LIDER`/`ACTIVISTA`: si las migraciones previas añadieron los **valores en minúscula**, usar `ADD VALUE 'lider'`/`'activista'`; si añadieron los **nombres en mayúscula**, usar `'LIDER'`/`'ACTIVISTA'`. Este paso es la lección de [[prod-recovery-alembic-enums]] — confirmar antes de aplicar a prod.

- [ ] **Step 3: Verificar migración en SQLite (offline upgrade)**

Run:
```bash
cd backend && python -c "
from alembic.config import Config; from alembic import command
import tempfile, os
db = tempfile.mktemp(suffix='.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + db
cfg = Config('alembic.ini')
command.upgrade(cfg, 'head')
command.downgrade(cfg, '0007')
print('migration up/down OK')
"
```
Expected: `migration up/down OK` (sin excepciones).

- [ ] **Step 4: Smoke en PostGIS (si hay docker disponible)**

Run (opcional pero recomendado, como en SP0b-2b):
```bash
docker run -d --rm -e POSTGRES_PASSWORD=agora -e POSTGRES_USER=agora -e POSTGRES_DB=agora -p 5433:5432 postgis/postgis:17-3.5
# esperar readiness, luego:
cd backend && DATABASE_URL="postgresql+psycopg://agora:agora@localhost:5433/agora" python -c "
from alembic.config import Config; from alembic import command
command.upgrade(Config('alembic.ini'), 'head'); print('PG 0001->0008 OK')
"
```
Expected: `PG 0001->0008 OK`; `registros` existe con `clave_elector_enc` BYTEA.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/0008_activistas.py
git commit -m "feat(spa1): Alembic 0008 — registros table + users lider_id/seccion + roles"
```

---

## Task 5: Login por teléfono o email

**Files:**
- Modify: `backend/app/services/auth_service.py`, `backend/app/schemas/auth.py`, `backend/app/routers/auth.py`
- Test: `backend/tests/test_auth.py` (añadir)

**Interfaces:**
- Consumes: `authenticate_user`, `LoginRequest`.
- Produces: `authenticate_user(db, identifier: str, password: str) -> User | None` (resuelve por email o phone); `LoginRequest.identifier`.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_auth.py` (usa el activista con phone seedeado):
```python
def test_login_by_phone(client):
    resp = client.post("/api/auth/login", json={"identifier": "5550000001", "password": "password123"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_login_by_email_via_identifier(client):
    resp = client.post("/api/auth/login", json={"identifier": "admin@alpha.gov", "password": "password123"})
    assert resp.status_code == 200, resp.text
```
(`client` fixture y `password123` ya existen en conftest.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_auth.py::test_login_by_phone -v`
Expected: FAIL (422: el schema exige `email`, no acepta `identifier`).

- [ ] **Step 3: Actualizar el schema**

En `backend/app/schemas/auth.py`, reemplazar `LoginRequest`:
```python
class LoginRequest(BaseModel):
    # Accepts an email or a phone number. ``email`` kept as optional alias for
    # backward compatibility with the existing frontend payload.
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @classmethod
    def _coerce(cls, data):  # not a validator; see model_validator below
        return data
```
Y reemplazar el import superior `from pydantic import BaseModel, EmailStr, Field` por `from pydantic import BaseModel, Field, model_validator`. Añadir, dentro de `LoginRequest`, un validador que acepte el viejo campo `email`:
```python
    @model_validator(mode="before")
    @classmethod
    def _accept_email_alias(cls, data):
        if isinstance(data, dict) and "identifier" not in data and "email" in data:
            data = {**data, "identifier": data["email"]}
        return data
```
(Elimina el método `_coerce` placeholder; era ilustrativo — no lo incluyas.)

- [ ] **Step 4: Actualizar el servicio**

En `backend/app/services/auth_service.py`, reemplazar `authenticate_user`:
```python
from sqlalchemy import or_, select


def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
    """Return the user if credentials are valid. ``identifier`` is email or phone."""
    user = db.execute(
        select(User).where(
            or_(User.email == identifier, User.phone == identifier),
            User.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
```
(Asegurar el import `or_` junto al `select` existente.)

- [ ] **Step 5: Actualizar el router**

En `backend/app/routers/auth.py`, en `login`, cambiar la llamada a:
```python
    user = auth_service.authenticate_user(db, payload.identifier, payload.password)
```
Y el detalle de error a `"Invalid credentials"`.

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: PASS (incluidos los tests previos de auth — el alias `email` mantiene compatibilidad).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/schemas/auth.py backend/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat(spa1): login by phone or email (identifier field, email alias kept)"
```

---

## Task 6: Fundamento multitenant — bypass superadmin en scoping

**Files:**
- Modify: `backend/app/core/scoping.py`, `backend/app/dependencies.py`
- Test: `backend/tests/test_scoping.py` (añadir), `backend/tests/test_tenancy.py` (verificar no-regresión)

**Interfaces:**
- Consumes: `scoped_query(model, ctx)`, `get_campaign_context`.
- Produces: `scoped_query` omite filtros org/campaign cuando `ctx.is_superadmin and ctx.organization_id is None`; `CampaignContext` de un superadmin adopta `organization_id = campaign.organization_id`.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_scoping.py`:
```python
def test_scoped_query_superadmin_no_base_skips_filters():
    sql = str(scoped_query(Contest, _Ctx(None, None, is_super=True)))
    assert "organization_id" not in sql
    assert "campaign_id" not in sql


def test_scoped_query_superadmin_with_base_filters():
    # Superadmin scoped into a base (org adopted) → normal filtering.
    sql = str(scoped_query(Contest, _Ctx("org1", "camp1", is_super=True)))
    assert "organization_id" in sql and "campaign_id" in sql


def test_scoped_query_normal_user_unchanged():
    sql = str(scoped_query(Contest, _Ctx("org1", "camp1", is_super=False)))
    assert "organization_id" in sql and "campaign_id" in sql
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_scoping.py -v`
Expected: FAIL (el superadmin sin base hoy genera `organization_id IS NULL` filter, no lo omite).

- [ ] **Step 3: Implementar el bypass en scoping**

En `backend/app/core/scoping.py`, reemplazar el cuerpo de `scoped_query` por:
```python
    stmt = select(model)
    cols = model.__table__.c

    if "deleted_at" in cols:
        stmt = stmt.where(cols.deleted_at.is_(None))

    # Superadmin with no base selected → consolidated view across all tenants.
    superadmin_all = getattr(ctx, "is_superadmin", False) and ctx.organization_id is None
    if superadmin_all:
        return stmt

    if "organization_id" in cols:
        if cols.organization_id.nullable:
            stmt = stmt.where(or_(cols.organization_id.is_(None), cols.organization_id == ctx.organization_id))
        else:
            stmt = stmt.where(cols.organization_id == ctx.organization_id)

    if "campaign_id" in cols:
        stmt = stmt.where(cols.campaign_id == ctx.campaign_id)

    return stmt
```
(Actualizar el docstring para mencionar el modo consolidado del superadmin.)

- [ ] **Step 4: Corregir get_campaign_context para el superadmin**

En `backend/app/dependencies.py`, en `get_campaign_context`, cambiar el `return` final para que el superadmin adopte la org de la campaña seleccionada:
```python
    organization_id = campaign.organization_id if ctx.is_superadmin else ctx.organization_id
    return CampaignContext(
        user=ctx.user, organization_id=organization_id, role=ctx.role, campaign_id=x_campaign_id
    )
```

- [ ] **Step 5: Run tests + no-regresión de tenancy**

Run: `cd backend && pytest tests/test_scoping.py tests/test_tenancy.py -v`
Expected: PASS (scoping nuevo + aislamiento de usuarios normales intacto).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/scoping.py backend/app/dependencies.py backend/tests/test_scoping.py
git commit -m "feat(spa1): superadmin cross-tenant scoping bypass + base-org adoption"
```

---

## Task 7: Servicio de registros (CRUD + cripto + consent + idempotencia + audit)

**Files:**
- Create: `backend/app/services/registro_service.py`
- Test: `backend/tests/test_registros.py` (añadir tests de servicio)

**Interfaces:**
- Consumes: `Registro`, schemas, `crypto`, `scoped_query`, `record_audit`, `CampaignContext`, `User`, `UserRole`.
- Produces:
  - `create_registro(db, ctx: CampaignContext, data: RegistroCreate) -> Registro`
  - `list_registros(db, ctx: CampaignContext, q: str | None, limit: int, offset: int) -> tuple[list[Registro], int]`
  - `get_registro(db, ctx: CampaignContext, registro_id: str) -> Registro | None`
  - `update_registro(db, ctx, registro_id, data: RegistroUpdate) -> Registro | None`
  - `delete_registro(db, ctx, registro_id) -> bool`
  - `ConsentRequired` (Exception)

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_registros.py`:
```python
def test_consent_required_raises():
    from app.services import registro_service
    from app.schemas.registro import RegistroCreate
    db = TestingSessionLocal()
    try:
        ctx = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        data = RegistroCreate(nombre_completo="Sin Consent", consentimiento=False)
        import pytest
        with pytest.raises(registro_service.ConsentRequired):
            registro_service.create_registro(db, ctx, data)
    finally:
        db.query(__import__("app.models.registro", fromlist=["Registro"]).Registro).delete()
        db.commit(); db.close()
```
Y añadir un helper al inicio del archivo de test:
```python
def _camp_ctx(db, email, campaign_id):
    from sqlalchemy import select
    from app.dependencies import CampaignContext
    from app.models.user import User
    from app.models.campaign import Campaign
    user = db.execute(select(User).where(User.email == email)).scalar_one()
    camp = db.execute(select(Campaign).where(Campaign.id == campaign_id)).scalar_one()
    org = camp.organization_id if user.role.value == "superadmin" else user.organization_id
    return CampaignContext(user=user, organization_id=org, role=user.role, campaign_id=campaign_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_registros.py::test_consent_required_raises -v`
Expected: FAIL (ModuleNotFoundError: app.services.registro_service)

- [ ] **Step 3: Implementar el servicio**

Crear `backend/app/services/registro_service.py`:
```python
"""Registro service — capture CRUD with encryption, consent, idempotency, audit."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import crypto
from app.core.scoping import scoped_query
from app.dependencies import CampaignContext
from app.models.registro import Registro
from app.models.user import User, UserRole
from app.schemas.registro import RegistroCreate, RegistroUpdate
from app.services.audit_service import record_audit

AVISO_VERSION = "v1"


class ConsentRequired(Exception):
    """Raised when a registro is created/updated without consentimiento=True."""


def _role_scoped(db: Session, ctx: CampaignContext):
    """Base SELECT for registros, filtered by tenant/campaign AND role scope."""
    stmt = scoped_query(Registro, ctx)
    if ctx.is_superadmin:
        return stmt
    if ctx.role == UserRole.ACTIVISTA:
        return stmt.where(Registro.activista_id == ctx.user.id)
    if ctx.role == UserRole.LIDER:
        sub = select(User.id).where(User.lider_id == ctx.user.id)
        return stmt.where(or_(Registro.activista_id.in_(sub), Registro.activista_id == ctx.user.id))
    return stmt  # ADMIN: full campaign scope


def create_registro(db: Session, ctx: CampaignContext, data: RegistroCreate) -> Registro:
    if not data.consentimiento:
        raise ConsentRequired()

    # Idempotency: reuse an existing row with the same (campaign, client_uuid).
    if data.client_uuid:
        existing = db.execute(
            scoped_query(Registro, ctx).where(Registro.client_uuid == data.client_uuid)
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    clave_enc = crypto.encrypt_clave(data.clave_elector) if data.clave_elector else None
    clave_masked = crypto.mask_clave(data.clave_elector) if data.clave_elector else None

    reg = Registro(
        organization_id=ctx.organization_id,
        campaign_id=ctx.campaign_id,
        activista_id=ctx.user.id,
        nombre_completo=data.nombre_completo,
        seccion=data.seccion,
        direccion=data.direccion,
        colonia=data.colonia,
        telefono=data.telefono,
        area=data.area,
        clave_elector_enc=clave_enc,
        clave_masked=clave_masked,
        consentimiento=True,
        consentimiento_at=datetime.now(timezone.utc),
        aviso_version=AVISO_VERSION,
        client_uuid=data.client_uuid,
        lat=data.lat,
        lng=data.lng,
        created_by=ctx.user.id,
    )
    db.add(reg)
    db.flush()
    record_audit(db, action="registro.create", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="registro", entity_id=reg.id)
    db.commit()
    db.refresh(reg)
    return reg


def list_registros(db: Session, ctx: CampaignContext, q: Optional[str], limit: int, offset: int):
    stmt = _role_scoped(db, ctx)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Registro.nombre_completo.ilike(like), Registro.seccion.ilike(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Registro.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return rows, total


def get_registro(db: Session, ctx: CampaignContext, registro_id: str) -> Optional[Registro]:
    return db.execute(
        _role_scoped(db, ctx).where(Registro.id == registro_id)
    ).scalar_one_or_none()


def update_registro(db, ctx, registro_id, data: RegistroUpdate) -> Optional[Registro]:
    reg = get_registro(db, ctx, registro_id)
    if reg is None:
        return None
    if data.consentimiento is False:
        raise ConsentRequired()
    fields = data.model_dump(exclude_unset=True)
    if "clave_elector" in fields:
        clave = fields.pop("clave_elector")
        reg.clave_elector_enc = crypto.encrypt_clave(clave) if clave else None
        reg.clave_masked = crypto.mask_clave(clave) if clave else None
    fields.pop("consentimiento", None)
    for k, v in fields.items():
        setattr(reg, k, v)
    reg.updated_by = ctx.user.id
    db.flush()
    record_audit(db, action="registro.update", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="registro", entity_id=reg.id)
    db.commit()
    db.refresh(reg)
    return reg


def delete_registro(db, ctx, registro_id) -> bool:
    reg = get_registro(db, ctx, registro_id)
    if reg is None:
        return False
    reg.deleted_at = datetime.now(timezone.utc)
    reg.updated_by = ctx.user.id
    db.flush()
    record_audit(db, action="registro.delete", actor_id=ctx.user.id,
                 organization_id=ctx.organization_id, entity_type="registro", entity_id=reg.id)
    db.commit()
    return True
```

- [ ] **Step 4: Añadir tests de servicio (scope por rol + idempotencia)**

Añadir a `backend/tests/test_registros.py`:
```python
def _make(db, ctx, nombre, **kw):
    from app.services import registro_service
    from app.schemas.registro import RegistroCreate
    return registro_service.create_registro(
        db, ctx, RegistroCreate(nombre_completo=nombre, consentimiento=True, **kw))


def test_activista_sees_only_own_lider_sees_structure():
    from app.services import registro_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        a2 = _camp_ctx(db, "activista2@alpha.gov", ALPHA_CAMPAIGN_ID)
        lider = _camp_ctx(db, "lider@alpha.gov", ALPHA_CAMPAIGN_ID)
        _make(db, a1, "Persona A1")
        _make(db, a2, "Persona A2")
        own, total_own = registro_service.list_registros(db, a1, None, 50, 0)
        assert {r.nombre_completo for r in own} == {"Persona A1"}
        seen, total_l = registro_service.list_registros(db, lider, None, 50, 0)
        assert {r.nombre_completo for r in seen} == {"Persona A1", "Persona A2"}
    finally:
        db.query(Registro).delete(); db.commit(); db.close()


def test_idempotent_client_uuid():
    from app.services import registro_service
    db = TestingSessionLocal()
    try:
        a1 = _camp_ctx(db, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
        r1 = _make(db, a1, "Dup", client_uuid="cu-1")
        r2 = _make(db, a1, "Dup", client_uuid="cu-1")
        assert r1.id == r2.id
        _, total = registro_service.list_registros(db, a1, None, 50, 0)
        assert total == 1
    finally:
        db.query(Registro).delete(); db.commit(); db.close()
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_registros.py -v`
Expected: PASS (consent, scope por rol, idempotencia).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/registro_service.py backend/tests/test_registros.py
git commit -m "feat(spa1): registro service — CRUD, crypto, consent, idempotency, role scope, audit"
```

---

## Task 8: Router de registros + perfil + registro en main + tests de API/permisos

**Files:**
- Create: `backend/app/routers/registros.py`, `backend/tests/test_registro_permissions.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `registro_service`, schemas, `CampaignCtx`, `Tenant`, `require_roles`.
- Produces: router con `POST/GET/PUT/DELETE /api/registros`, `GET /api/registros/mios`, `GET /api/perfil`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_registro_permissions.py`:
```python
"""API-level permission + lifecycle tests for /registros."""
from tests.conftest import auth_headers, ALPHA_CAMPAIGN_ID, BETA_CAMPAIGN_ID


def _hdr(client, email, campaign_id):
    h = auth_headers(client, email)
    h["X-Campaign-Id"] = campaign_id
    return h


def test_capture_cycle_and_consent(client):
    h = _hdr(client, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
    # consent false -> 422
    bad = client.post("/api/registros", json={"nombre_completo": "No Consent", "consentimiento": False}, headers=h)
    assert bad.status_code == 422, bad.text
    # create
    ok = client.post("/api/registros", json={
        "nombre_completo": "María López", "seccion": "0001",
        "clave_elector": "ABCD1234567890XYZ8", "consentimiento": True}, headers=h)
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["clave_masked"] == "****-XYZ8"
    assert "clave_elector_enc" not in body and "clave_elector" not in body
    rid = body["id"]
    # list
    lst = client.get("/api/registros/mios", headers=h)
    assert lst.status_code == 200 and lst.json()["total"] >= 1
    # delete
    dele = client.delete(f"/api/registros/{rid}", headers=h)
    assert dele.status_code == 204


def test_activista_cannot_see_other_activista(client):
    h1 = _hdr(client, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
    h2 = _hdr(client, "activista2@alpha.gov", ALPHA_CAMPAIGN_ID)
    created = client.post("/api/registros", json={"nombre_completo": "Solo A1", "consentimiento": True}, headers=h1)
    rid = created.json()["id"]
    # activista2 cannot fetch activista1's registro
    assert client.get(f"/api/registros/{rid}", headers=h2).status_code == 404
    client.delete(f"/api/registros/{rid}", headers=h1)


def test_superadmin_can_capture_in_any_base(client):
    h = _hdr(client, "super@atlas.gov", BETA_CAMPAIGN_ID)
    ok = client.post("/api/registros", json={"nombre_completo": "Super en Beta", "consentimiento": True}, headers=h)
    assert ok.status_code == 201, ok.text
    assert ok.json()["organization_id"]  # adopted from the selected base
    client.delete(f"/api/registros/{ok.json()['id']}", headers=h)


def test_perfil_returns_lider_name(client):
    h = auth_headers(client, "activista1@alpha.gov")
    resp = client.get("/api/perfil", headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["lider_nombre"] == "Alpha Líder"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_registro_permissions.py -v`
Expected: FAIL (404: rutas `/registros` no existen).

- [ ] **Step 3: Crear el router**

Crear `backend/app/routers/registros.py`:
```python
"""Activist capture router: /registros + /perfil."""
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.dependencies import CampaignCtx, DbSession, Tenant
from app.models.user import User
from app.schemas.registro import (
    PerfilRead, RegistroCreate, RegistroList, RegistroRead, RegistroUpdate,
)
from app.services import registro_service

router = APIRouter(tags=["registros"])


@router.post("/registros", response_model=RegistroRead, status_code=201)
def create(data: RegistroCreate, db: DbSession, ctx: CampaignCtx) -> RegistroRead:
    if ctx.is_superadmin and not ctx.organization_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a base first")
    try:
        reg = registro_service.create_registro(db, ctx, data)
    except registro_service.ConsentRequired:
        raise HTTPException(status_code=422, detail="Consentimiento es obligatorio")
    return RegistroRead.model_validate(reg)


@router.get("/registros/mios", response_model=RegistroList)
def list_mine(
    db: DbSession, ctx: CampaignCtx,
    q: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RegistroList:
    rows, total = registro_service.list_registros(db, ctx, q, limit, offset)
    return RegistroList(items=[RegistroRead.model_validate(r) for r in rows],
                        total=total, limit=limit, offset=offset)


@router.get("/registros/{registro_id}", response_model=RegistroRead)
def get_one(registro_id: str, db: DbSession, ctx: CampaignCtx) -> RegistroRead:
    reg = registro_service.get_registro(db, ctx, registro_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registro not found")
    return RegistroRead.model_validate(reg)


@router.put("/registros/{registro_id}", response_model=RegistroRead)
def update(registro_id: str, data: RegistroUpdate, db: DbSession, ctx: CampaignCtx) -> RegistroRead:
    try:
        reg = registro_service.update_registro(db, ctx, registro_id, data)
    except registro_service.ConsentRequired:
        raise HTTPException(status_code=422, detail="Consentimiento es obligatorio")
    if reg is None:
        raise HTTPException(status_code=404, detail="Registro not found")
    return RegistroRead.model_validate(reg)


@router.delete("/registros/{registro_id}", status_code=204)
def delete(registro_id: str, db: DbSession, ctx: CampaignCtx) -> None:
    if not registro_service.delete_registro(db, ctx, registro_id):
        raise HTTPException(status_code=404, detail="Registro not found")


@router.get("/perfil", response_model=PerfilRead)
def perfil(db: DbSession, ctx: Tenant) -> PerfilRead:
    lider_nombre = None
    if ctx.user.lider_id:
        lider = db.execute(select(User).where(User.id == ctx.user.lider_id)).scalar_one_or_none()
        lider_nombre = lider.full_name if lider else None
    return PerfilRead(
        id=ctx.user.id, full_name=ctx.user.full_name, role=ctx.user.role,
        seccion=ctx.user.seccion, lider_id=ctx.user.lider_id,
        lider_nombre=lider_nombre, organization_id=ctx.organization_id,
    )
```

- [ ] **Step 4: Registrar el router + crypto en startup**

En `backend/app/main.py`:
- En el bloque `from app.routers import (...)` añadir `registros`.
- En la tupla de módulos que se registran (donde está `app.include_router(module.router, prefix=prefix)`), añadir `registros` a la lista de módulos.
- En el `lifespan`/startup (donde corre el bootstrap), añadir tras los imports:
```python
        from app.core.crypto import ensure_crypto_ready
        ensure_crypto_ready()
```
(Falla rápido si `FERNET_KEY` no está configurada.)

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_registro_permissions.py -v`
Expected: PASS (ciclo, consent 422, aislamiento activista, superadmin en base ajena, perfil).

- [ ] **Step 6: Run full backend suite**

Run: `cd backend && pytest -q`
Expected: PASS (sin regresiones).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/registros.py backend/app/main.py backend/tests/test_registro_permissions.py
git commit -m "feat(spa1): registros + perfil router, registered in app, crypto startup check"
```

---

## Task 9: Frontend — módulo de captura + login por identificador

**Files:**
- Create: `frontend/src/api/registros.ts`, `frontend/src/modules/captura/CapturaPage.tsx`
- Modify: `frontend/src/modules/registry.ts`, `frontend/src/pages/LoginPage.tsx`

**Interfaces:**
- Consumes: `apiClient` (envía `Authorization` + `X-Campaign-Id`), patrón de módulo existente.
- Produces: cliente `registros`; página `CapturaPage`; entrada de módulo `captura`.

- [ ] **Step 1: Inspeccionar patrones existentes**

Leer `frontend/src/api/client.ts`, un cliente existente (p.ej. `frontend/src/api/campaigns.ts`), `frontend/src/modules/registry.ts` y `frontend/src/pages/LoginPage.tsx` para replicar el patrón exacto (cómo se inyecta `X-Campaign-Id`, cómo se define un `ModuleDef`, cómo `useAsync`/`DataState` se usan).

- [ ] **Step 2: Crear el cliente API**

Crear `frontend/src/api/registros.ts`:
```typescript
import { apiClient } from "./client";

export interface Registro {
  id: string;
  nombre_completo: string;
  seccion: string | null;
  direccion: string | null;
  colonia: string | null;
  telefono: string | null;
  area: string | null;
  clave_masked: string | null;
  consentimiento: boolean;
  created_at: string;
}

export interface RegistroList {
  items: Registro[];
  total: number;
  limit: number;
  offset: number;
}

export interface RegistroCreate {
  nombre_completo: string;
  seccion?: string;
  direccion?: string;
  colonia?: string;
  telefono?: string;
  area?: string;
  clave_elector?: string;
  consentimiento: boolean;
  client_uuid?: string;
}

export interface Perfil {
  id: string;
  full_name: string;
  role: string;
  seccion: string | null;
  lider_id: string | null;
  lider_nombre: string | null;
  organization_id: string | null;
}

export async function getPerfil(): Promise<Perfil> {
  const { data } = await apiClient.get<Perfil>("/perfil");
  return data;
}

export async function listMisRegistros(q?: string): Promise<RegistroList> {
  const { data } = await apiClient.get<RegistroList>("/registros/mios", { params: q ? { q } : {} });
  return data;
}

export async function createRegistro(payload: RegistroCreate): Promise<Registro> {
  const { data } = await apiClient.post<Registro>("/registros", payload);
  return data;
}

export async function deleteRegistro(id: string): Promise<void> {
  await apiClient.delete(`/registros/${id}`);
}
```

- [ ] **Step 3: Crear la página de captura (adaptando la semilla)**

Crear `frontend/src/modules/captura/CapturaPage.tsx` adaptando `docs/registro-activista.jsx`:
- Conservar el layout/estilos de la semilla (header navy, cards, aviso de privacidad colapsable, consent checkbox, validación de clave 18-char con hint, lista de personas con borrar).
- Reemplazar el bloque "Datos del activista" (manual) por datos de `getPerfil()` (nombre del activista, su líder, sección) mostrados en solo-lectura.
- Añadir el input **Área/Programa** al formulario (`area`).
- `Guardar` → `createRegistro({...})` (envía `consentimiento` y `clave_elector` en claro al backend, que cifra). Tras éxito, recargar `listMisRegistros()`.
- La lista viene de `listMisRegistros()`; borrar → `deleteRegistro(id)`.
- **Quitar** los botones de export Excel/CSV (llegan en SPA-4).
- Usar el patrón `useAsync`/`DataState` existente para estados de carga/vacío ("Aún no hay registros…").
- Tipar todo (TS); sin `any`.

> El componente debe enviar `X-Campaign-Id` implícitamente vía `apiClient` (que ya lo inyecta desde el store de campaña activa). Verificar que el activista tenga una campaña activa seleccionada; si no, mostrar un aviso.

- [ ] **Step 4: Registrar el módulo**

En `frontend/src/modules/registry.ts`, añadir una entrada `captura` siguiendo el shape de las demás (path `/captura`, label "Captura", icono apropiado de lucide, `roles: ["ACTIVISTA","LIDER","ADMIN"]` según el patrón de roles del registry, componente lazy `() => import("./captura/CapturaPage")`).

- [ ] **Step 5: Login por identificador**

En `frontend/src/pages/LoginPage.tsx`, cambiar el campo de email por un campo **identificador** (label "Teléfono o correo", `type="text"`), y enviar `{ identifier, password }` al endpoint de login (el backend acepta también `email` por compatibilidad). Ajustar el cliente `frontend/src/api/auth.ts` si tipa el payload de login.

- [ ] **Step 6: Build**

Run: `cd frontend && npm run build`
Expected: build verde, sin errores de TS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/registros.ts frontend/src/modules/captura/CapturaPage.tsx frontend/src/modules/registry.ts frontend/src/pages/LoginPage.tsx frontend/src/api/auth.ts
git commit -m "feat(spa1): captura module (adapted seed) + login by phone/email identifier"
```

---

## Self-Review

**Spec coverage:**
- §3.1 registros → Task 3/4 ✓ · §3.2 User roles/lider_id → Task 2/4 ✓ (+ `seccion` añadido, necesario para perfil) · §3.3 Alembic 0008 → Task 4 ✓
- §4 crypto/consent/audit → Task 1/7 ✓ · §5 login phone/email → Task 5 ✓
- §6 superadmin scoping → Task 6 ✓ · §7 API → Task 7/8 ✓ · §8 frontend → Task 9 ✓ · §9 tests → distribuidos ✓
- Fuera de alcance (reveal, consola consolidada, offline, export) → no hay tareas, correcto.

**Placeholder scan:** El método `_coerce` en Task 5 Step 3 está marcado explícitamente como ilustrativo a NO incluir; el resto es código completo. Sin TBD/TODO.

**Type consistency:** `create_registro/list_registros/get_registro/update_registro/delete_registro` y `ConsentRequired` consistentes entre Task 7 (definición) y Task 8 (uso). Schemas (`RegistroCreate/Read/List/Update/PerfilRead`) consistentes entre Task 3 (def) y Task 7/8 (uso). `crypto.encrypt_clave/mask_clave/decrypt_clave/ensure_crypto_ready` consistentes (Task 1 def, Task 7/8 uso). `scoped_query` firma sin cambios.

**Nota de implementación cross-task:** el orden de seed en conftest (Task 3) debe persistir `org_a`/`org_b` antes de referenciarlos; seguir el orden indicado (flush tras crear orgs, luego usuarios, luego campañas).
