# SPA-4 · Compliance + Export/Reports + QA/Security/Deploy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar el programa de activistas con (Fase 7) el cumplimiento legal bloqueante para producción — clave cifrada verificada, aviso de privacidad versionado con traza de aceptación, ARCO hard-delete, retención/purga y limpieza de logs/URLs —; (Fase 8) export Excel/CSV + reportes por sección respetando scope y enmascaramiento con reveal auditado; y (Fase 9) QA, security hardening (rate-limit, headers, CORS), load test y promoción QA→beta→prod en Railway.

**Architecture:** Extiende el spine existente reutilizando `crypto`, `registro_service`, `scoped_query`, `record_audit`, `require_roles`. Nuevos modelos (`PrivacyNotice`, `PrivacyAcceptance`, `ArcoRequest`), servicios (`privacy_service`, `arco_service`, `retention_service`, `export_service`, `report_service`), routers (`privacy`, `arco`, `exports`, `reports`) y un CLI de purga. Capas: `models/` → `schemas/` → `services/` → `routers/`, igual que SPA-1.

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · Alembic 1.14 · Pydantic v2 · `cryptography` (Fernet, ya integrado) · **`openpyxl==3.1.5` (YA en requirements)** + `csv` stdlib para export · `httpx` (ya) para load test · **rate-limiting: `slowapi` (dependencia nueva, pendiente de confirmar)** o middleware propio · React 18 + TS para el ajuste del aviso en `CapturaPage`.

## Global Constraints

- **Spec de referencia:** `docs/superpowers/specs/2026-06-29-spa4-compliance-export-deploy-design.md`. Toda tarea hereda sus reglas y criterios de aceptación (AC-7.x bloqueantes).
- **Golden Rules (`docs/architecture.md`):** queries filtran por `organization_id`; tenant/campaign de escrituras viene del contexto, nunca del body; endpoints devuelven Pydantic, nunca ORM; RBAC en API (`require_roles`); operaciones sensibles emiten `AuditLog`; sin secretos hardcodeados; listas `{items,total,limit,offset}`; errores `{ "error": { "message", "status" } }`.
- **Cifrado:** `decrypt_clave` solo en call-sites permitidos (reveal de SPA-2 + export-reveal de SPA-4). Ningún payload/export/log de rol no privilegiado expone clave en claro. **Nunca PII en `audit_log.meta`** (solo conteos/ids/flags).
- **Migraciones:** patrones endurecidos (`_table_exists`/`_index_exists`, enums por NOMBRE mayúscula + `create_type=False`, `ADD VALUE IF NOT EXISTS` en bloque autocommit como `0003`, dialect-safe PG/SQLite, sin `try/except` de flujo). **Revisiones placeholder** (`00XX_*`): el head efectivo depende de SPA-2/SPA-3 → `down_revision` se **reconcilia al integrar** (documentarlo en cada archivo). Registrar modelos en `app/models/__init__.py` y tablas en `tests/conftest.py`.
- **Tests:** SQLite in-memory (`tests/conftest.py`), reusando el seed de SPA-1. Suite completa verde, sin regresiones. Frontend `npm run build` verde.
- **Compliance gate:** ninguna promoción a `production` (Task 11) hasta que **todos los AC-7.x** (Tasks 2–6) estén verdes.
- **Rama:** crear `feat/spa4-compliance-export-deploy` desde el head integrado de SPA-3 (no desde `main` directamente, salvo que SPA-2/SPA-3 ya estén en `main`).

---

## File Structure

**Backend — crear:**
- `backend/app/models/privacy.py` — `PrivacyNotice`, `PrivacyAcceptance`.
- `backend/app/models/arco.py` — `ArcoRequest` (+ enums `ArcoTipo`, `ArcoEstado`).
- `backend/app/schemas/privacy.py`, `backend/app/schemas/arco.py`, `backend/app/schemas/export.py` (params), `backend/app/schemas/report.py`.
- `backend/app/services/privacy_service.py`, `arco_service.py`, `retention_service.py`, `export_service.py`, `report_service.py`.
- `backend/app/routers/privacy.py`, `arco.py`, `exports.py`, `reports.py`.
- `backend/app/middleware/security_headers.py` (security headers middleware).
- `backend/alembic/versions/00XX_privacy.py`, `00XX_arco.py` (placeholders).
- `backend/scripts/../scripts/purge_registros.py`, `scripts/loadtest_capture.py`.
- Tests: `backend/tests/test_privacy.py`, `test_arco.py`, `test_retention.py`, `test_export.py`, `test_reports.py`, `test_security.py`, `test_integration_flows.py`.

**Backend — modificar:**
- `backend/requirements.txt` — (si se elige) `slowapi`.
- `backend/app/core/config.py` — `RETENTION_*`, settings de rate-limit/headers.
- `backend/app/core/logging.py` — redacción de PII en errores de validación si aplica.
- `backend/app/services/registro_service.py` — `create_registro` usa aviso activo + escribe `PrivacyAcceptance` (sustituye `AVISO_VERSION`).
- `backend/app/main.py` — registrar routers nuevos; montar security-headers middleware; rate limiter; redacción en `validation_exception_handler`.
- `backend/app/models/__init__.py` — registrar modelos nuevos.
- `backend/tests/conftest.py` — tablas nuevas + seed de aviso global `v1`.
- `backend/app/bootstrap.py` — seed idempotente del aviso global `v1`.

**Frontend — modificar:**
- `frontend/src/api/registros.ts` o nuevo `frontend/src/api/privacy.ts` — `getActiveNotice()`; cliente de export (descarga blob).
- `frontend/src/modules/captura/CapturaPage.tsx` — aviso desde API; botón de export.

**Docs — modificar/crear:**
- `CLAUDE.md`, `STATUS.md` — estado + runbook (Task 11).

---

## Task 1: Config + dependencias (retención, rate-limit, settings) — *foundation, no paralelo*

**Files:**
- Modify: `backend/app/core/config.py`, `backend/requirements.txt`
- Test: `backend/tests/test_security.py` (crear; primer test de config)

**Interfaces:**
- Produces: `settings.RETENTION_ENABLED: bool`, `settings.RETENTION_DAYS_AFTER_ELECTION: int`, `settings.RETENTION_PURGE_SOFT_DELETED_DAYS: int`, `settings.LOGIN_RATE_LIMIT: str` (p.ej. `"5/minute"`), `settings.SECURITY_HEADERS_ENABLED: bool`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_security.py`:
```python
from app.core.config import settings

def test_retention_settings_have_safe_defaults():
    assert settings.RETENTION_ENABLED is False
    assert settings.RETENTION_DAYS_AFTER_ELECTION >= 0
    assert settings.RETENTION_PURGE_SOFT_DELETED_DAYS >= 0

def test_login_rate_limit_configured():
    assert isinstance(settings.LOGIN_RATE_LIMIT, str) and "/" in settings.LOGIN_RATE_LIMIT
```
- [ ] **Step 2: Run to verify it fails** — `cd backend && pytest tests/test_security.py -v` → FAIL (AttributeError).
- [ ] **Step 3: Add settings** en `config.py` (sección nueva `# --- Compliance / Retention ---` y `# --- Hardening ---`):
```python
    RETENTION_ENABLED: bool = Field(default=False)
    RETENTION_DAYS_AFTER_ELECTION: int = Field(default=180)
    RETENTION_PURGE_SOFT_DELETED_DAYS: int = Field(default=30)
    LOGIN_RATE_LIMIT: str = Field(default="5/minute")
    SECURITY_HEADERS_ENABLED: bool = Field(default=True)
```
- [ ] **Step 4: (Decisión humano) dependencia rate-limit** — si se aprueba `slowapi`, añadir a `requirements.txt` bajo `# --- Security ---`: `slowapi==0.1.9` e instalar. Si se elige middleware propio, omitir (se implementa en Task 9 sin dependencia).
- [ ] **Step 5: Run to verify it passes** — `pytest tests/test_security.py -v` → PASS.
- [ ] **Step 6: Commit** — `feat(spa4): compliance/retention/hardening settings`.

---

## Task 2: Aviso de privacidad versionado — modelos + migración + seed (AC-7.2)

**Files:**
- Create: `backend/app/models/privacy.py`, `backend/app/schemas/privacy.py`, `backend/alembic/versions/00XX_privacy.py`
- Modify: `backend/app/models/__init__.py`, `backend/tests/conftest.py`, `backend/app/bootstrap.py`
- Test: `backend/tests/test_privacy.py`

**Interfaces:**
- Consumes: mixins `UUIDMixin/TenantMixin/AuditMixin`, `Registro`.
- Produces: `PrivacyNotice` (tabla `privacy_notices`), `PrivacyAcceptance` (tabla `privacy_acceptances`); schemas `PrivacyNoticeRead/Create`, `PrivacyAcceptanceRead`; seed de aviso global `v1`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_privacy.py`: model imports + tabla en metadata; `PrivacyNotice.__table__.c` incluye `organization_id` (nullable), `version`, `body`, `is_active`; `PrivacyAcceptance` incluye `registro_id`, `notice_id`, `aviso_version`.
- [ ] **Step 2: Run to verify it fails** — FAIL (ModuleNotFoundError).
- [ ] **Step 3: Crear modelos** en `backend/app/models/privacy.py` (`organization_id` NULLABLE = aviso global; `UniqueConstraint(organization_id, version)`; índice `(organization_id, is_active)`; `body: Text`; `PrivacyAcceptance.registro_id` FK `registros.id` ondelete CASCADE).
- [ ] **Step 4: Registrar en metadata** — `app/models/__init__.py` (import + `__all__`) y `tests/conftest.py` (`create_all` tablas + import).
- [ ] **Step 5: Crear schemas** — `backend/app/schemas/privacy.py` (`PrivacyNoticeRead` con `from_attributes`, `PrivacyNoticeCreate` con `version`+`body`, `PrivacyAcceptanceRead`).
- [ ] **Step 6: Migración placeholder** — `00XX_privacy.py` con helpers `_table_exists`/`_index_exists`, dialect-safe; **comentario** explicando que `down_revision` se reconcilia al integrar sobre el head de SPA-3.
- [ ] **Step 7: Seed idempotente del aviso global `v1`** — en `bootstrap.py` (y en `conftest.py` seed): crear `PrivacyNotice(organization_id=None, version="v1", is_active=True, body=<texto actual de CapturaPage>)` si no existe.
- [ ] **Step 8: Verificar migración SQLite up/down** (patrón SPA-1 Task 4 Step 3) → `migration up/down OK`.
- [ ] **Step 9: Run tests** — `pytest tests/test_privacy.py -v` + `pytest -q` sin regresiones.
- [ ] **Step 10: Commit** — `feat(spa4): PrivacyNotice + PrivacyAcceptance models, migration, global v1 seed`.

---

## Task 3: Servicio + endpoints de aviso + enlace en `create_registro` (AC-7.2)

**Files:**
- Create: `backend/app/services/privacy_service.py`, `backend/app/routers/privacy.py`
- Modify: `backend/app/services/registro_service.py`, `backend/app/main.py`
- Test: `backend/tests/test_privacy.py` (añadir)

**Interfaces:**
- Produces: `privacy_service.get_active_notice(db, ctx) -> PrivacyNotice`, `publish_notice(db, ctx, data) -> PrivacyNotice`, `record_acceptance(db, ctx, registro, notice)`; router `GET /api/privacy/notice`, `GET /api/privacy/notices`, `POST /api/privacy/notices`.
- Consumes: `record_audit`, `scoped_query`, `require_roles`.

- [ ] **Step 1: Write the failing test** — crear registro escribe `PrivacyAcceptance` con la versión activa; publicar `v2` deja la aceptación `v1` previa intacta; sin aviso activo, `create_registro` falla con error claro (no `AVISO_VERSION` hardcoded).
- [ ] **Step 2: Run to verify it fails** — FAIL.
- [ ] **Step 3: `privacy_service`** — `get_active_notice` (base activa → fallback global), `publish_notice` (desactiva anterior, crea activa, `record_audit("privacy.notice.publish")`), `record_acceptance` (crea `PrivacyAcceptance` + `record_audit("privacy.accept")`).
- [ ] **Step 4: Modificar `registro_service.create_registro`** — sustituir `aviso_version=AVISO_VERSION` por `notice = privacy_service.get_active_notice(db, ctx)`; `registro.aviso_version = notice.version`; tras `flush`, `privacy_service.record_acceptance(...)`; misma transacción. Eliminar la constante `AVISO_VERSION` (o dejar de usarla).
- [ ] **Step 5: Router `privacy.py`** — endpoints; `GET /notice` accesible a roles de captura; `GET/POST /notices` gated `require_roles(ADMIN)` (superadmin auto-pasa). Registrar en `main.py`.
- [ ] **Step 6: Frontend** — `CapturaPage.tsx` consume `GET /api/privacy/notice` (cuerpo + versión) en vez del texto estático; el checkbox referencia la versión. `npm run build` verde.
- [ ] **Step 7: Run tests** — `pytest tests/test_privacy.py tests/test_registros.py -v` + `pytest -q` sin regresiones.
- [ ] **Step 8: Commit** — `feat(spa4): versioned privacy notice service + endpoints + acceptance trail in create_registro`.

---

## Task 4: ARCO hard-delete — modelo + servicio + endpoints (AC-7.3) — *paralelo con Task 5/6 tras Task 1*

**Files:**
- Create: `backend/app/models/arco.py`, `backend/app/schemas/arco.py`, `backend/app/services/arco_service.py`, `backend/app/routers/arco.py`, `backend/alembic/versions/00XX_arco.py`
- Modify: `backend/app/models/__init__.py`, `backend/tests/conftest.py`, `backend/app/main.py`
- Test: `backend/tests/test_arco.py`

**Interfaces:**
- Produces: `ArcoRequest` (+ enums `ArcoTipo`/`ArcoEstado`); `arco_service.create_request(...)`, `hard_delete_titular(db, ctx, *, request_id, registro_ids) -> int`; router `POST /api/arco/solicitudes`, `POST /api/arco/solicitudes/{id}/ejecutar`, `GET /api/arco/solicitudes`.
- Consumes: `scoped_query`, `record_audit`, `require_roles(ADMIN)`.

- [ ] **Step 1: Write the failing test** — hard-delete elimina **físicamente** los `registro`s + sus `PrivacyAcceptance` (CASCADE); deja audit `registro.hard_delete`; idempotente (segunda ejecución no-op); admin de otra base no puede borrar ajenos (404/403); `titular_ref` nunca contiene clave completa.
- [ ] **Step 2: Run to verify it fails** — FAIL.
- [ ] **Step 3: Modelo `arco.py`** — `ArcoRequest` con enums por NOMBRE mayúscula (`create_type=False` para reuso PG); columnas de §3.3 (sin PII completa).
- [ ] **Step 4: Servicio `arco_service`** — `hard_delete_titular` resuelve vía `_role_scoped`/`scoped_query` (admin/superadmin), `db.delete(reg)` físico, audit por registro (`meta={"arco_request_id","count"}`), marca `ArcoRequest` PROCESADA; idempotente.
- [ ] **Step 5: Router `arco.py`** gated admin/superadmin; registrar en `main.py`.
- [ ] **Step 6: Migración placeholder `00XX_arco.py`** — tabla + enums (patrón endurecido + autocommit para `ADD VALUE`); registrar modelo en `__init__.py` + tabla en `conftest.py`. Verificar SQLite up/down.
- [ ] **Step 7: Run tests** — `pytest tests/test_arco.py -v` + `pytest -q`.
- [ ] **Step 8: Commit** — `feat(spa4): ARCO hard-delete (ArcoRequest model + service + endpoints + audit)`.

---

## Task 5: Retención / purga — servicio + CLI (AC-7.4) — *paralelo con Task 4/6 tras Task 1*

**Files:**
- Create: `backend/app/services/retention_service.py`, `scripts/purge_registros.py`
- Test: `backend/tests/test_retention.py`

**Interfaces:**
- Produces: `retention_service.purge_expired(db, *, now, dry_run=False) -> PurgeResult` (dataclass con conteos por campaña + total).
- Consumes: `Contest.election_date`, `Registro`, `record_audit`, `settings.RETENTION_*`.

- [ ] **Step 1: Write the failing test** — con `RETENTION_ENABLED=False` no borra; con `election_date` + `RETENTION_DAYS_AFTER_ELECTION` vencidos hace **hard-delete** y audita (`retention.purge`); purga física de soft-deleted más viejos que `RETENTION_PURGE_SOFT_DELETED_DAYS`; `dry_run=True` reporta sin borrar; segunda corrida = no-op.
- [ ] **Step 2: Run to verify it fails** — FAIL.
- [ ] **Step 3: Servicio `retention_service`** — itera campañas con `Contest.election_date`, calcula vencimiento, hard-delete idempotente + audit; respeta `RETENTION_ENABLED`; soporta `dry_run`.
- [ ] **Step 4: CLI `scripts/purge_registros.py`** — patrón `scripts/ingest_file.py` (`sys.path.insert` backend, `SessionLocal`, `argparse` con `--dry-run`/`--apply`), imprime resumen. Documentar como cron/one-off Railway (no en lifespan).
- [ ] **Step 5: Run tests** — `pytest tests/test_retention.py -v` + `pytest -q`.
- [ ] **Step 6: Commit** — `feat(spa4): configurable retention purge service + CLI (idempotent, audited)`.

---

## Task 6: Higiene de logs/URLs + clave enmascarada por defecto (AC-7.5, AC-7.6, AC-7.1) — *paralelo tras Task 1*

**Files:**
- Modify: `backend/app/main.py` (`validation_exception_handler` redacta `clave_elector`), `backend/app/core/logging.py` (si aplica)
- Test: `backend/tests/test_security.py` (añadir)

**Interfaces:**
- Produces: redacción de `clave_elector` en `details` de errores 422; helper de redacción reutilizable.

- [ ] **Step 1: Write the failing test** — POST `/registros` con `clave_elector` inválida → el cuerpo 422 **no** contiene el valor enviado (redactado a `"***"`). Test que `RegistroRead`/export de un `LIDER` jamás incluyen clave en claro. Grep-test: `decrypt_clave` solo aparece en call-sites permitidos.
- [ ] **Step 2: Run to verify it fails** — FAIL (hoy `exc.errors()` filtra el `input`).
- [ ] **Step 3: Implementar redacción** — en `validation_exception_handler`, mapear `exc.errors()` y reemplazar el `input`/`loc` de campos sensibles (`clave_elector`, `password`) por `"***"`. Documentar en checklist que `auth.login` audita solo `ip` y que `q` de captura no se loggea.
- [ ] **Step 4: Run tests** — `pytest tests/test_security.py -v` + `pytest -q`.
- [ ] **Step 5: Commit** — `feat(spa4): redact sensitive fields from validation errors; log/URL hygiene checks`.

> **Gate de Fase 7:** al cerrar Tasks 2–6, marcar AC-7.1…AC-7.6 verdes en `STATUS.md` (Task 11). Es prerequisito de la promoción a prod.

---

## Task 7: Export Excel + CSV con scope + máscara + reveal auditado (AC-8.1, AC-8.2) — *paralelo con Task 8*

**Files:**
- Create: `backend/app/services/export_service.py`, `backend/app/routers/exports.py`, `backend/app/schemas/export.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_export.py`

**Interfaces:**
- Produces: `export_service.build_registros_export(db, ctx, *, fmt, filters, reveal) -> (bytes, filename, media_type)`; router `GET /api/registros/export`.
- Consumes: `registro_service._role_scoped`, `crypto.decrypt_clave` (solo reveal), `openpyxl`, `csv`, `record_audit`, `require_roles`.

- [ ] **Step 1: Write the failing test** — export `xlsx` y `csv` respetan `_role_scoped` (activista solo lo suyo; líder su estructura); incluyen encabezado de estructura; **clave enmascarada por defecto**; `reveal=true` como `ACTIVISTA`/`LIDER` → `403`; `reveal=true` como `ADMIN` → clave en claro + audit `registro.export.reveal`; todo export emite audit `registro.export` (sin claves en `meta`).
- [ ] **Step 2: Run to verify it fails** — FAIL (ruta inexistente).
- [ ] **Step 3: `export_service`** — xlsx con `openpyxl` (`Workbook`→`BytesIO`), csv con `csv` stdlib (`StringIO`); encabezado (campaña, base, exportador, rol, fecha, total, reveal flag); columnas de §4.1; clave = `clave_masked` salvo reveal autorizado.
- [ ] **Step 4: Router `exports.py`** — `GET /registros/export?format=&q=&seccion=&reveal=`; `StreamingResponse` + `Content-Disposition`; gate de reveal (ADMIN/SUPERADMIN — reusar el de SPA-2 si existe); audit. Registrar en `main.py`.
- [ ] **Step 5: Frontend** — botón "Exportar" en `CapturaPage`/consola que descarga el blob. `npm run build` verde.
- [ ] **Step 6: Run tests** — `pytest tests/test_export.py -v` + `pytest -q`.
- [ ] **Step 7: Commit** — `feat(spa4): registros export (xlsx/csv) — role scope, masked-by-default, audited reveal`.

---

## Task 8: Reporte por sección + cobertura opcional (AC-8.3) — *paralelo con Task 7*

**Files:**
- Create: `backend/app/services/report_service.py`, `backend/app/routers/reports.py`, `backend/app/schemas/report.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reports.py`

**Interfaces:**
- Produces: `report_service.por_seccion(db, ctx) -> list[SeccionCount]`; router `GET /api/reports/secciones` (+ `?format=` reusa `export_service`); `GET /api/reports/secciones/cobertura.geojson` (OPCIONAL).
- Consumes: `registro_service._role_scoped`, patrón GeoJSON del router `maps` (`ST_AsGeoJSON`).

- [ ] **Step 1: Write the failing test** — `/reports/secciones` agrega `COUNT GROUP BY seccion` respetando scope por rol; export del reporte funciona; cobertura geojson devuelve `FeatureCollection` (vacío si no hay cartografía de secciones).
- [ ] **Step 2: Run to verify it fails** — FAIL.
- [ ] **Step 3: `report_service` + router** — agregación scoped; cobertura opcional vía join con `ElectoralArea` (degradación elegante si no hay secciones). Registrar en `main.py`.
- [ ] **Step 4: Run tests** — `pytest tests/test_reports.py -v` + `pytest -q`.
- [ ] **Step 5: Commit** — `feat(spa4): report por sección (scoped, exportable) + optional cobertura geojson`.

---

## Task 9: Security hardening — rate-limit login + security headers + CORS (AC-9.2) — *paralelo tras Task 1*

**Files:**
- Create: `backend/app/middleware/security_headers.py`
- Modify: `backend/app/main.py`, `backend/app/routers/auth.py`, (si slowapi) `requirements.txt`
- Test: `backend/tests/test_security.py` (añadir)

**Interfaces:**
- Produces: middleware de security headers; rate-limit en `POST /auth/login` (`429` en envelope).

- [ ] **Step 1: Write the failing test** — N+1 logins desde la misma IP en la ventana → `429` con envelope `{error:{message,status}}`; respuestas incluyen `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, (prod) `Strict-Transport-Security`.
- [ ] **Step 2: Run to verify it fails** — FAIL.
- [ ] **Step 3: Security headers middleware** — Starlette `BaseHTTPMiddleware` que setea headers (gated por `SECURITY_HEADERS_ENABLED` + `is_production` para HSTS); CSP mínima compatible con SPA + MapLibre. Montar en `create_app()` antes del catch-all.
- [ ] **Step 4: Rate limiting** — si `slowapi`: `Limiter` en `app.state.limiter`, handler `RateLimitExceeded`→envelope `429`, `@limiter.limit(settings.LOGIN_RATE_LIMIT)` en `login`. Si middleware propio: ventana fija en memoria por IP (documentar limitación 1-réplica).
- [ ] **Step 5: CORS** — verificar `CORS_ORIGINS` por entorno (no `localhost` en prod); documentar en runbook.
- [ ] **Step 6: Run tests** — `pytest tests/test_security.py -v` + `pytest -q`.
- [ ] **Step 7: Commit** — `feat(spa4): login rate limiting + security headers middleware + CORS review`.

---

## Task 10: Tests de integración + load test ligero (AC-9.1)

**Files:**
- Create: `backend/tests/test_integration_flows.py`, `scripts/loadtest_capture.py`
- Test: el propio archivo de integración.

**Interfaces:**
- Consumes: `client` fixture + seed de SPA-1; todos los endpoints SPA-1…SPA-4.

- [ ] **Step 1: Flujo activista E2E** — login (teléfono) → `/perfil` → `/privacy/notice` → `POST /registros` → `/registros/mios` → `/registros/export` (enmascarado). Verde.
- [ ] **Step 2: Flujo admin E2E** — publicar `v2` → export `reveal=true` (audit) → ARCO `POST /solicitudes` + `ejecutar` (hard-delete verificado) → `/reports/secciones` → `/audit` muestra las acciones sensibles.
- [ ] **Step 3: Load test CLI** — `scripts/loadtest_capture.py` (`asyncio`+`httpx`): N capturas concurrentes contra qa/beta, reporta p50/p95/errores. Sin dependencia nueva.
- [ ] **Step 4: Run full suite** — `cd backend && pytest -q` verde; `cd frontend && npm run build` verde.
- [ ] **Step 5: Commit** — `test(spa4): activist+admin integration flows + concurrent capture load test`.

---

## Task 11: Deploy QA→beta→prod + `CLAUDE.md`/`STATUS.md` (AC-9.3)

**Files:**
- Modify/Create: `CLAUDE.md`, `STATUS.md`
- (Infra) Railway: entornos qa/beta/prod, variables, cron de purga.

**Interfaces:**
- Produces: runbook + gate de compliance documentado.

- [ ] **Step 1: Reconciliar migraciones** — fijar los `down_revision` reales de `00XX_privacy`/`00XX_arco` sobre el head efectivo (post SPA-2/SPA-3); correr `alembic upgrade head` en SQLite y PostGIS (smoke) → OK.
- [ ] **Step 2: Variables por entorno** — confirmar en qa/beta/prod: `FERNET_KEY` (distinta por entorno), `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `RETENTION_*`, `LOGIN_RATE_LIMIT`. (Usar las herramientas Railway MCP / dashboard; **no** commitear secretos.)
- [ ] **Step 3: Promoción** — desplegar a qa → validar AC-7.x verdes (gate) → beta → smoke → prod. Configurar cron/one-off de `scripts/purge_registros.py` en beta/prod.
- [ ] **Step 4: Docs** — `STATUS.md` con estado SPA-1…SPA-4, checklist AC-7.x verde, env vars, cómo correr el purge, próximos pasos; `CLAUDE.md` con notas del módulo de activistas.
- [ ] **Step 5: Commit** — `docs(spa4): deploy runbook + STATUS/CLAUDE update; compliance gate green`.

---

## Self-Review

**Cobertura de spec:**
- Fase 7: AC-7.1 → Task 6 (+ verificación transversal) ✓ · AC-7.2 → Task 2/3 ✓ · AC-7.3 → Task 4 ✓ · AC-7.4 → Task 5 ✓ · AC-7.5 → Task 6 ✓ · AC-7.6 → Task 6/7 ✓
- Fase 8: AC-8.1/8.2 → Task 7 ✓ · AC-8.3 → Task 8 ✓
- Fase 9: AC-9.1 → Task 10 ✓ · AC-9.2 → Task 9 ✓ · AC-9.3 → Task 11 ✓

**Orden por dependencia:** Task 1 (foundation) → [Task 2→3] (privacy, secuencial: 3 depende del modelo de 2 y modifica `create_registro`) ∥ [Task 4, Task 5, Task 6] (paralelos entre sí y con la cadena de privacy, archivos disjuntos) → [Task 7 ∥ Task 8] (export/reportes, archivos disjuntos) ∥ Task 9 (hardening, toca `main.py`/`auth.py`) → Task 10 (integración, depende de casi todo) → Task 11 (deploy, último).

**Tareas paralelo-safe (archivos disjuntos):**
- Task 4 ∥ Task 5 ∥ Task 6 (tras Task 1): `arco.py`/`arco_service.py` vs `retention_service.py`/`scripts/purge_registros.py` vs `logging.py`/`test_security.py` + `main.py` (handler). *Cuidado:* Task 4, 9 y 7/8 **todas registran routers en `main.py`** → conflicto de merge esperable en ese archivo; resolver registrando routers en bloque al integrar (no es conflicto lógico).
- Task 7 ∥ Task 8 (export vs reportes).
- Task 9 puede correr en paralelo desde el inicio (tras Task 1), pero comparte `main.py` con varios → integrar con cuidado.

**Riesgos / notas:**
- `main.py` es punto de contención (registro de routers + middlewares). Integrar cambios de Task 4/7/8/9 secuencialmente o reservar un sub-paso de integración.
- Numeración Alembic: revisiones **placeholder** hasta conocer el head de SPA-2/SPA-3; reconciliar en Task 11 Step 1.
- Dependencia `slowapi`: confirmar antes de Task 1 Step 4 / Task 9 Step 4 (alternativa middleware propio sin dependencia).
- Export **no** requiere dependencia nueva (`openpyxl` ya está, `csv` stdlib).
- `AVISO_VERSION` constante en `registro_service` se elimina en Task 3 → asegurar que ningún test de SPA-1 dependa de ella (ajustar si rompe).
