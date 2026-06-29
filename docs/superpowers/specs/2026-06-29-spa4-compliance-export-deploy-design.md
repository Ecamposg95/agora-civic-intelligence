# SPA-4 · Compliance + Export/Reports + QA/Security/Deploy — Design

- **Fecha:** 2026-06-29
- **Programa:** AGORA — Plataforma de Captura y Gestión de Activistas (vertical dentro de `agora-civic-intelligence`, stack Atlas)
- **Sub-proyecto:** SPA-4 (cuarta y última rebanada del Task Pack Maestro de Activistas)
- **Estado:** diseño aprobado en brainstorming, pendiente de plan de implementación
- **Task Pack origen:** Fase 7 (cumplimiento — **bloqueante para prod**), Fase 8 (export/reportes), Fase 9 (QA/seguridad/deploy)
- **Depende de:** SPA-1 (núcleo de captura, mergeado: modelo `Registro`, `crypto`, `registro_service`, `/registros`, `/perfil`), **SPA-2** (consola admin/superadmin: revelar-clave con audit, `/admin/registros`, catálogo de áreas) y **SPA-3** (PWA offline). SPA-4 asume que SPA-2 y SPA-3 están integrados cuando arranca.

---

## 1. Objetivo y encuadre

SPA-4 cierra el programa de activistas con lo que **no es negociable para producción**: cumplimiento legal de datos personales (Fase 7), la capacidad de **exportar y reportar** respetando scope y enmascaramiento (Fase 8), y el **endurecimiento + promoción a producción** (Fase 9).

La Fase 7 es **bloqueante**: ningún despliegue a `production` puede ocurrir hasta que **todos** los criterios de aceptación de §3 estén verdes. El resto de fases son entregables de valor que se construyen sobre el mismo spine ya existente.

**Reúso del spine existente (verificado en código):**
- Cifrado: `app/core/crypto.py` (`encrypt_clave`/`decrypt_clave`/`mask_clave`/`ensure_crypto_ready`, Fernet, fail-fast sin `FERNET_KEY`).
- Modelo: `app/models/registro.py` (`Registro` con `clave_elector_enc: LargeBinary`, `clave_masked`, `consentimiento`, `consentimiento_at`, `aviso_version: String(40)`, `deleted_at` soft-delete vía `AuditMixin`).
- Servicio: `app/services/registro_service.py` (`_role_scoped(ctx)`, `create/list/get/update/delete_registro`, `AVISO_VERSION = "v1"` hardcoded, `delete_registro` hace **soft-delete**).
- Scoping: `app/core/scoping.py` (`scoped_query` — chokepoint único; bypass superadmin; excluye `deleted_at`).
- Audit: `app/services/audit_service.py` (`record_audit(...)` append-only; `list_events`), modelo `app/models/audit_log.py` (`meta` JSONB; "Never store secrets or raw PII in meta").
- RBAC: `app/dependencies.py` (`require_roles`, `CampaignCtx`, `Tenant`, `CampaignContext`).
- App: `app/main.py` (`_configure_cors`, error-envelope handlers, `lifespan` con `ensure_crypto_ready()` + bootstrap; **sin** rate-limiting ni security-headers hoy).
- Export infra: **`openpyxl==3.1.5` YA está en `requirements.txt`** (usado por ingestión). `csv` es stdlib. **No se requiere dependencia nueva para export.**
- Jobs/CLI: patrón `scripts/*.py` (p.ej. `scripts/ingest_file.py`): `sys.path.insert` a `backend/`, `SessionLocal`, `_CliCtx` con `is_superadmin=True`. Railway corre estos vía cron/one-off.
- Retención: `Contest.election_date: Optional[date]` (`app/models/campaign.py`) — fuente natural de la fecha de elección por campaña.

**Golden Rules (de `docs/architecture.md`) que SPA-4 hereda:** queries filtran por `organization_id`; escrituras toman tenant del contexto; endpoints devuelven Pydantic; RBAC en API; operaciones sensibles emiten `audit_log`; sin secretos hardcodeados; listas `{items,total,limit,offset}`; errores `{ "error": { "message", "status" } }`.

---

## 2. Alcance

### En alcance (SPA-4)

**Fase 7 — Compliance (bloqueante):**
1. **Clave cifrada en reposo en todo el sistema** — verificación auditada + tests de regresión (no plaintext en columnas, payloads, exports ni logs).
2. **Aviso de privacidad VERSIONADO + registro de aceptación** — modelo `PrivacyNotice` (versión + cuerpo + `published_at` + `is_active`) y `PrivacyAcceptance` (traza por registro de qué versión aceptó el titular). El alta de `registro` enlaza la versión activa en vez de `"v1"` hardcoded.
3. **ARCO (hard-delete del titular)** — endpoint admin-only, auditado, que **elimina permanentemente** los `registro`(s) de un titular (vs. el soft-delete de SPA-1). Bitácora de solicitud `ArcoRequest`.
4. **Retención/purga** — job configurable por env (vigencia post-elección), idempotente y auditado, corrible por CLI/cron en Railway.
5. **Higiene de logs/URLs** — revisión de que ningún dato personal viaje en logs ni en URLs; tests/checks.
6. **Clave enmascarada por defecto en TODAS las vistas de líder** — verificación de que ninguna respuesta/exportación de rol no-privilegiado expone clave en claro.

**Fase 8 — Export/Reportes:**
7. **Export Excel (xlsx) + CSV** con encabezado de activista/estructura, respetando scope por rol; clave **enmascarada por defecto**.
8. **Reveal de clave en export** solo con permiso explícito (rol privilegiado), y **cada reveal auditado** (consistente con el `revelar-clave` de SPA-2).
9. **Reporte por sección electoral** (conteos agregados, scoped) + **mapa de cobertura por sección (opcional)**.

**Fase 9 — QA/Seguridad/Deploy:**
10. **Tests de integración** de flujos activista + admin.
11. **Security review**: rate-limiting en login, validación de input, CORS, security headers.
12. **Load test ligero** (captura concurrente).
13. **Promoción QA → beta → prod** en Railway.
14. **`CLAUDE.md` / `STATUS.md`** con estado y próximos pasos.

### Fuera de alcance
- Consola admin/superadmin de UI, `/admin/registros`, dashboards consolidados, catálogo de áreas administrable, **endpoint de revelar-clave puntual** → **SPA-2** (SPA-4 reutiliza su patrón de audit para el reveal en export).
- PWA offline, cola IndexedDB, sync → **SPA-3**.
- Portal de autoservicio para el titular (las solicitudes ARCO entran por canal externo y las procesa un admin).
- Borrado criptográfico por rotación de `FERNET_KEY` / key management avanzado (se documenta como riesgo, no se implementa).
- WAF/CDN externos, pentest formal de terceros.

---

## 3. Fase 7 — Compliance (BLOQUEANTE)

> **Regla de oro de la fase:** cada ítem de esta sección es un **criterio de aceptación**. El gate de deploy a `production` (Fase 9) NO se levanta hasta que todos estén verdes con evidencia (test verde o check documentado).

### 3.1 Clave cifrada en reposo en todo el sistema (AC-7.1)
Verificación, no construcción nueva (el cifrado existe desde SPA-1):
- `Registro` solo persiste `clave_elector_enc` (BYTEA/`LargeBinary`) + `clave_masked`; **nunca** una columna en claro. (Confirmado.)
- `create_registro`/`update_registro` cifran vía `crypto.encrypt_clave`. (Confirmado.)
- `RegistroRead` **no** expone `clave_elector_enc` ni clave en claro (solo `clave_masked`). (Confirmado.)
- **Nuevos** invariantes que SPA-4 debe cubrir: export (Fase 8) y cualquier endpoint admin de SPA-2 jamás emiten clave en claro salvo el flujo reveal auditado.
- **Criterio:** test que recorre todas las rutas de salida (`RegistroRead`, export xlsx/csv sin reveal, report por sección) y verifica ausencia del valor en claro; grep de CI que prohíbe `decrypt_clave` fuera de los call-sites permitidos (reveal de SPA-2 + export-reveal de SPA-4).

### 3.2 Aviso de privacidad versionado + registro de aceptación (AC-7.2)

**Estado actual:** `CapturaPage.tsx` tiene el aviso como **texto estático** y `registro_service.AVISO_VERSION = "v1"` está **hardcoded**. SPA-4 lo convierte en una **entidad versionada** con traza de aceptación.

**Modelo `PrivacyNotice`** (tabla `privacy_notices`) — mixins `UUIDMixin` + `TenantMixin` (org NULLABLE) + `AuditMixin`:

| Columna | Tipo | Notas |
|---|---|---|
| `id` | UUID(str36) | PK |
| `organization_id` | FK organizations | **NULLABLE** — `NULL` = aviso global de plataforma (default); no-NULL = aviso propio de la base |
| `version` | String(40) | etiqueta de versión (`"v1"`, `"v2"`…); única por org |
| `body` | Text | cuerpo legal completo (Markdown/plano) |
| `published_at` | DateTime(tz) | cuándo entró en vigor |
| `is_active` | Boolean | exactamente uno activo por org (o global) |
| `created_by` | str36 | quién publicó (admin/superadmin) |

`__table_args__`: `UniqueConstraint(organization_id, version)`; índice `(organization_id, is_active)`.

**Resolución del aviso activo:** para una base dada, el aviso activo es el `PrivacyNotice` con `is_active=True` y `organization_id == ctx.organization_id`; si no existe, cae al global (`organization_id IS NULL`, `is_active=True`). Esto encaja con el patrón de "reference data nullable org" ya soportado por `scoped_query`.

**Modelo `PrivacyAcceptance`** (tabla `privacy_acceptances`) — `UUIDMixin` + `TenantMixin`:

| Columna | Tipo | Notas |
|---|---|---|
| `id` | UUID(str36) | PK |
| `organization_id` | FK organizations | de la base |
| `registro_id` | FK registros.id (ondelete CASCADE) | el registro al que pertenece el consentimiento |
| `notice_id` | FK privacy_notices.id | versión exacta aceptada |
| `aviso_version` | String(40) | denormalizado (resiliente a borrado de notice) |
| `accepted_at` | DateTime(tz) | = `consentimiento_at` del registro |
| `accepted_by` | str36 | activista que capturó (responsable del tratamiento) |

> **Por qué una tabla aparte y no solo `registro.aviso_version`:** la traza de aceptación es evidencia legal que debe sobrevivir a la edición del registro y enlazar a la **versión exacta** del texto mostrado. `registro.aviso_version` (string, ya existe) se mantiene como denormalización rápida; `PrivacyAcceptance` es el registro formal.

**Flujo:**
- `create_registro` deja de usar `AVISO_VERSION` constante: llama a `privacy_service.get_active_notice(db, ctx)`, escribe `registro.aviso_version = notice.version` y, tras `flush`, crea un `PrivacyAcceptance` enlazado. Todo en la misma transacción + `record_audit(action="privacy.accept")`.
- Si no hay aviso activo (ni de base ni global) → `create_registro` falla con error claro (no se captura sin aviso vigente). Bootstrap/seed garantiza un aviso global `"v1"` con el texto actual de `CapturaPage`.

**Endpoints (`app/routers/privacy.py`):**
- `GET /api/privacy/notice` → aviso activo para la base actual (público para roles de captura; lo consume el formulario). `200 PrivacyNoticeRead`.
- `GET /api/privacy/notices` → historial de versiones (admin/superadmin). `Page[PrivacyNoticeRead]`.
- `POST /api/privacy/notices` → publica una versión nueva (admin/superadmin): marca la anterior `is_active=False`, crea la nueva activa. Auditado `privacy.notice.publish`.

**Frontend:** `CapturaPage.tsx` reemplaza el texto estático por `GET /api/privacy/notice` (cuerpo + versión visibles); el checkbox de consentimiento referencia la versión mostrada.

**Criterio AC-7.2:** crear un registro escribe `PrivacyAcceptance` con la versión activa; publicar `v2` no altera la aceptación `v1` previa; sin aviso activo no se puede capturar.

### 3.3 ARCO — hard-delete del titular (AC-7.3)

**Estado actual:** `delete_registro` hace **soft-delete** (`deleted_at = now`). ARCO (derecho de cancelación) exige **borrado permanente**.

**Modelo `ArcoRequest`** (tabla `arco_requests`) — `UUIDMixin` + `TenantMixin` + `AuditMixin` — bitácora de la solicitud (evidencia de cumplimiento, **sin PII sensible**):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | UUID(str36) | PK |
| `organization_id` | FK organizations | base |
| `tipo` | Enum `ArcoTipo` (`ACCESO`/`RECTIFICACION`/`CANCELACION`/`OPOSICION`) | SPA-4 implementa **CANCELACION** (hard-delete); el resto reservado |
| `titular_ref` | String(255) | identificador del titular **enmascarado/parcial** (p.ej. nombre + últimos 4 de clave) — nunca clave completa |
| `motivo` | String(500) | nullable, libre |
| `estado` | Enum (`PENDIENTE`/`PROCESADA`/`RECHAZADA`) | |
| `registros_afectados` | Integer | conteo de filas eliminadas |
| `processed_by` | str36 | admin que ejecutó |
| `processed_at` | DateTime(tz) | |

**Servicio `arco_service.hard_delete_titular(db, ctx, *, registro_ids: list[str], request_id, motivo)`:**
- Resuelve los `registro` vía `_role_scoped`/`scoped_query` (admin/superadmin only) → garantiza tenant-safety.
- **Borra físicamente** las filas (`db.delete(reg)`), incluyendo las `PrivacyAcceptance` enlazadas (CASCADE).
- Escribe `record_audit(action="registro.hard_delete", entity_type="registro", entity_id=<id>, meta={"arco_request_id": ..., "count": n})` por cada registro (meta sin PII).
- Marca `ArcoRequest.estado=PROCESADA`, `registros_afectados=n`, `processed_by/at`. Idempotente: re-ejecutar una solicitud ya procesada es no-op.

**Endpoints (`app/routers/arco.py`, admin/superadmin):**
- `POST /api/arco/solicitudes` → registra una `ArcoRequest` (PENDIENTE).
- `POST /api/arco/solicitudes/{id}/ejecutar` → corre el hard-delete (CANCELACION). `200` con `{registros_afectados}`.
- `GET /api/arco/solicitudes` → `Page[ArcoRequestRead]` (auditoría de cumplimiento).

**Criterio AC-7.3:** tras `ejecutar`, los `registro`s del titular **no existen** en la tabla (no solo `deleted_at`), sus `PrivacyAcceptance` tampoco, y queda audit `registro.hard_delete`. Un admin de otra base no puede borrar registros ajenos (404/403).

### 3.4 Retención / purga post-elección (AC-7.4)

**Config (env, en `app/core/config.py`):**
- `RETENTION_ENABLED: bool = False` (default seguro: no purga hasta activarlo).
- `RETENTION_DAYS_AFTER_ELECTION: int = 180` (**propuesto** — confirmar con negocio).
- `RETENTION_PURGE_SOFT_DELETED_DAYS: int = 30` (purga física de filas con `deleted_at` más viejas que N).

**Fuente de la fecha de elección:** `Contest.election_date` (existe) de los contests de la campaña; si una campaña no tiene contest con fecha, se omite (no se purga). Override por env para despliegues sin contests cargados (documentado).

**Servicio `retention_service.purge_expired(db, *, now, dry_run=False) -> PurgeResult`:**
- Para cada campaña con `election_date` + `RETENTION_DAYS_AFTER_ELECTION` ya cumplidos → **hard-delete** de sus `registro`s (vencimiento legal).
- Purga física de soft-deleted con `deleted_at < now - RETENTION_PURGE_SOFT_DELETED_DAYS`.
- **Idempotente** (re-correr no daña), **auditado** (`record_audit(action="retention.purge", meta={"campaign_id":..., "count":...})`), soporta `--dry-run`.

**CLI `scripts/purge_registros.py`** (patrón `scripts/ingest_file.py`): `argparse` con `--dry-run`/`--apply`, `SessionLocal`, imprime resumen. **Railway:** se documenta como cron/one-off job (no corre en el lifespan del web service para no acoplar arranque con purga).

**Criterio AC-7.4:** con `RETENTION_ENABLED=False` el job no borra nada; con fecha vencida borra físicamente y audita; `--dry-run` reporta sin borrar; segunda corrida = no-op.

### 3.5 Higiene de logs y URLs (AC-7.5)
- **Logs:** revisar que ningún `logger.*` ni el handler de excepciones (`app/main.py`) emita clave, teléfono, nombre o cuerpo de request. `auth.login` hoy audita `meta={"ip": ...}` (aceptable; IP es metadato operacional, documentado). El validation-handler devuelve `exc.errors()` que **puede** incluir el valor inválido enviado → revisar y **redactar** el campo `clave_elector` de los `details` antes de responder/loggear.
- **URLs:** los identificadores en path son UUID (no PII). El parámetro de búsqueda `q` (en `/registros/mios`) puede contener un nombre → **no loggear query strings** de endpoints de captura; confirmar que el access-log no los persista.
- **Criterio AC-7.5:** test que dispara una validación fallida con `clave_elector` inválida y verifica que el valor no aparece en el cuerpo del error; checklist documentado de revisión de logs.

### 3.6 Clave enmascarada por defecto en vistas de líder (AC-7.6)
- Ya garantizado por `RegistroRead` (solo `clave_masked`) y `_role_scoped` (un líder solo ve su estructura). SPA-4 **extiende** la garantía a export y reportes: para rol `LIDER`/`ACTIVISTA`/`ADMIN` sin permiso de reveal, la columna de clave en cualquier export es la enmascarada.
- **Criterio AC-7.6:** export como `LIDER` produce `clave_masked`, nunca clave en claro; el parámetro `reveal=true` es ignorado/403 para roles no privilegiados.

---

## 4. Fase 8 — Export / Reportes

### 4.1 Export Excel + CSV (`app/services/export_service.py` + `app/routers/exports.py`)

**Endpoints:**
- `GET /api/registros/export?format=xlsx|csv` → `StreamingResponse` con `Content-Disposition: attachment; filename="registros-<campaña>-<fecha>.<ext>"`.
- Acepta los mismos filtros que `list_registros` (`q`, `seccion`) y respeta `_role_scoped(ctx)` **exactamente** (un activista exporta solo lo suyo; un líder su estructura; admin la campaña; superadmin según base/consolidado).

**Formato:**
- **Encabezado de estructura** (filas superiores antes de la tabla): campaña, organización/base, activista o líder que exporta, rol, fecha/hora de generación, total de filas, y si la clave va enmascarada o revelada.
- **Columnas:** nombre_completo, sección, dirección, colonia, teléfono, área, **clave (enmascarada por defecto)**, consentimiento, aviso_version, fecha de captura, (para admin/superadmin) base y activista.
- **xlsx** vía `openpyxl` (ya instalado) — `Workbook` en memoria → `BytesIO`. **csv** vía `csv` stdlib → `StringIO`/`io`.
- Todo export emite `record_audit(action="registro.export", meta={"format":..., "rows":..., "reveal": bool})`.

### 4.2 Reveal de clave en export (AC consistente con SPA-2)
- `GET /api/registros/export?...&reveal=true` solo permitido para roles privilegiados (`ADMIN`/`SUPERADMIN`; **confirmar** si SPA-2 introduce un permiso fino — reusar su gate). Para roles no privilegiados, `reveal=true` → `403` (o se ignora silenciosamente devolviendo enmascarado; **decisión: 403 explícito**).
- Cuando `reveal=true` y autorizado: la columna de clave se descifra con `crypto.decrypt_clave` por fila, y se escribe **un audit por export** con `action="registro.export.reveal"`, `meta={"rows":..., "format":...}` (conteo, **sin** las claves). Esto es coherente con el `revelar-clave` puntual auditado de SPA-2.

### 4.3 Reporte por sección electoral (`app/services/report_service.py`)
- `GET /api/reports/secciones` → agregación `COUNT(*) GROUP BY seccion` sobre `_role_scoped(ctx)`; devuelve `{ items: [{seccion, total}], total }`. Exportable vía el mismo `export_service` (`?format=xlsx|csv`).
- Útil para medir cobertura territorial por activista/líder/campaña.

### 4.4 Mapa de cobertura por sección (OPCIONAL)
- `GET /api/reports/secciones/cobertura.geojson` → join de los conteos por sección con la geometría de `ElectoralArea` (nivel sección) usando el patrón GeoJSON existente del router `maps` (`ST_AsGeoJSON`). Marcado **opcional**: si la cartografía de secciones no está cargada para la base, el endpoint devuelve `FeatureCollection` vacío con aviso. Se prioriza solo si SPA-0b/maps tiene secciones disponibles.

---

## 5. Fase 9 — QA / Seguridad / Deploy

### 5.1 Tests de integración (activista + admin)
- Flujo activista E2E (API): login por teléfono → `GET /perfil` → `GET /privacy/notice` → `POST /registros` (con consentimiento + clave) → `GET /registros/mios` → `GET /registros/export` (enmascarado).
- Flujo admin E2E: publicar aviso `v2` → admin exporta con `reveal=true` (audit) → ARCO `POST /solicitudes` + `ejecutar` (hard-delete) → verificar audit + reporte por sección.
- Corren sobre SQLite in-memory (`tests/conftest.py`) reusando el seed de SPA-1 (lider/activistas/superadmin/beta).

### 5.2 Security review (concreto)
- **Rate limiting en login:** hoy `app/routers/auth.py` no limita. **Propuesta:** `slowapi` (**dependencia nueva**, depende de `limits`) — `Limiter(key_func=get_remote_address)` en `app.state.limiter`, handler `429` en envelope, decorador `@limiter.limit("5/minute")` en `POST /auth/login`. *Alternativa sin dependencia:* middleware Starlette propio con ventana fija en memoria (suficiente para 1 réplica; no distribuido). **Decisión pendiente del humano** (ver §7).
- **Validación de input:** ya cubierta por Pydantic v2 (longitudes, validador de clave 18-alfanum). Revisar límites de `limit` de paginación (ya `le=200`) y tamaños de body.
- **CORS:** `_configure_cors` usa orígenes explícitos desde `CORS_ORIGINS` (sin wildcard + credentials). **Acción:** confirmar que `CORS_ORIGINS` está correctamente seteado por entorno (qa/beta/prod) y no quedó el default `localhost`.
- **Security headers:** hoy ausentes. Añadir middleware Starlette propio (sin dependencia) que setee: `Strict-Transport-Security` (solo en prod/HTTPS), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, y una `Content-Security-Policy` mínima compatible con la SPA + MapLibre. Se monta en `create_app()` antes del catch-all SPA.

### 5.3 Load test ligero (captura concurrente)
- `scripts/loadtest_capture.py`: `asyncio` + `httpx.AsyncClient` que dispara N capturas concurrentes (login → POST /registros) contra un entorno qa/beta y reporta p50/p95/errores. Sin dependencia nueva (`httpx` ya está). Locust queda fuera de alcance.

### 5.4 Promoción QA → beta → prod (Railway)
- Entornos Railway: `qa` → `beta` → `production`. Cada uno con su `DATABASE_URL`, `FERNET_KEY` (distinta por entorno — **nunca** compartir), `CORS_ORIGINS`, `SECRET_KEY`, y las nuevas `RETENTION_*`.
- Migraciones Alembic corren en cada promoción (patrón endurecido; ver §6). El gate de promoción a `production` exige **todos los AC de Fase 7 verdes**.
- Cron/one-off para `scripts/purge_registros.py` se configura **solo** en beta/prod, no en qa.

### 5.5 `CLAUDE.md` / `STATUS.md`
- Actualizar/crear con: estado del programa de activistas (SPA-1…SPA-4), variables de entorno requeridas, cómo correr el purge job, gate de compliance, y próximos pasos.

---

## 6. Migraciones Alembic

SPA-4 añade tablas: `privacy_notices`, `privacy_acceptances`, `arco_requests` (+ enum `arco_tipo`/`arco_estado` en PG).

- **Numeración:** el head en la rama SPA-1 es `0008_activistas`. SPA-4 **apila después de las migraciones de SPA-2 y SPA-3**, cuyo número final aún no existe. **Se usan revisiones placeholder** (p.ej. `00XX_privacy_notices`, `00XX_arco`) y el `down_revision` real se **reconcilia al integrar** (rebase sobre el head efectivo). Documentar en cada archivo.
- **Patrones endurecidos obligatorios** (lección `prod-recovery-alembic-enums`): helpers `_table_exists`/`_index_exists`; enums por **NOMBRE en mayúscula** + `postgresql.ENUM(create_type=False)` cuando el tipo ya exista; `ADD VALUE IF NOT EXISTS` dentro de bloque autocommit (patrón `0003`); dialect-safe PG/SQLite; sin `try/except` de control de flujo; `downgrade` que no elimina valores de enum.
- Registrar los modelos nuevos en `app/models/__init__.py` y la tabla en `tests/conftest.py` (`create_all`).

---

## 7. Decisiones abiertas (para el humano)

1. **Vigencia de retención por defecto:** propuesto `RETENTION_DAYS_AFTER_ELECTION=180` y `RETENTION_ENABLED=False` por defecto. ¿Confirmar plazo legal aplicable?
2. **Librería de rate-limiting:** `slowapi` (nueva dependencia, idiomática FastAPI) vs. middleware propio sin dependencia (ventana fija en memoria, no distribuido). Recomendación: `slowapi` si se prevén múltiples réplicas con backend compartido; middleware propio si 1 réplica.
3. **Export:** **no requiere dependencia nueva** (`openpyxl` ya está; `csv` es stdlib). Confirmar que basta xlsx+csv (sin PDF).
4. **Alcance del aviso versionado:** propuesto org-level con default global (`organization_id` nullable). ¿Debe ser por campaña en vez de por organización?
5. **ARCO:** propuesto admin-only (titular solicita por canal externo). ¿Se requiere endpoint titular-facing self-service en este sub-proyecto?
6. **Reveal en export:** ¿reusar el gate/permiso fino que introduzca SPA-2, o basta `ADMIN`/`SUPERADMIN`?

---

## 8. Criterios de aceptación (resumen, gate de prod)

| ID | Criterio | Fase |
|---|---|---|
| AC-7.1 | Clave nunca en claro en columnas/payloads/exports/logs; `decrypt_clave` solo en call-sites permitidos | 7 (bloq.) |
| AC-7.2 | Aviso versionado + `PrivacyAcceptance` por registro; sin aviso activo no se captura | 7 (bloq.) |
| AC-7.3 | ARCO hard-delete admin-only, tenant-safe, auditado; elimina físicamente registro + aceptaciones | 7 (bloq.) |
| AC-7.4 | Purga configurable, idempotente, auditada, con `--dry-run`; off por defecto | 7 (bloq.) |
| AC-7.5 | Sin PII en logs ni URLs; `clave_elector` redactada de errores de validación | 7 (bloq.) |
| AC-7.6 | Clave enmascarada por defecto en todas las vistas/exports de líder | 7 (bloq.) |
| AC-8.1 | Export xlsx+csv con encabezado, scope por rol, audit | 8 |
| AC-8.2 | Reveal en export solo privilegiado + audit por export | 8 |
| AC-8.3 | Reporte por sección scoped; cobertura geojson opcional | 8 |
| AC-9.1 | Tests integración activista+admin verdes | 9 |
| AC-9.2 | Rate-limit login + security headers + CORS por entorno | 9 |
| AC-9.3 | Promoción qa→beta→prod con gate Fase 7; docs actualizadas | 9 |
