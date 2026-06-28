# SPA-1 · Núcleo de Captura de Activistas + Fundamento Multitenant — Design

- **Fecha:** 2026-06-27
- **Programa:** AGORA — Plataforma de Captura y Gestión de Activistas (vertical nuevo dentro de `agora-civic-intelligence`, stack Atlas)
- **Sub-proyecto:** SPA-1 (primera rebanada del Task Pack Maestro de Activistas)
- **Estado:** diseño aprobado en brainstorming, pendiente de plan de implementación
- **Semilla UI:** `docs/registro-activista.jsx`
- **Task Pack origen:** Fases 1–3 del pack + parte no-negociable de Fase 7 (cifrado + consentimiento) + fundamento multitenant/superadmin

---

## 1. Objetivo y encuadre

Digitalizar el "Formato Activista" físico: un **activista** captura personas contactadas (registros) desde el campo, y la plataforma las almacena de forma multitenant, segura y auditable. SPA-1 entrega el **núcleo de captura online** y el **fundamento multitenant correcto** (incluida la visibilidad cross-tenant del superadmin), sobre el cual se construyen los sub-proyectos siguientes.

**Encuadre confirmado:** AGORA-Activistas es un **módulo nuevo dentro del repo actual**, reutilizando el spine ya existente (`Organization`, `Campaign`, `User`, auth JWT, `scoped_query`, `AuditLog`, Alembic, frontend con module registry). Las Fases 0–2 del Task Pack son en su mayoría **reúso**, no construcción nueva.

**Decisiones de tenancy (locked):**
- Cada cliente/campaña = un `Organization` aislado = una "base".
- El **superadmin** es el operador de la plataforma y **gestiona TODO** cross-tenant (leer, crear, editar, borrar en cualquier base).
- En **modo consolidado** (sin base seleccionada) el superadmin ve registros de **todas las bases juntas**, cada fila etiquetada con su base/organización. *(La UI consolidada vive en SPA-2; SPA-1 entrega el fundamento de scoping que lo habilita.)*

## 2. Alcance

### En alcance (SPA-1)
1. Modelo `registros` (persona contactada) + migración Alembic 0008.
2. Extensión de `UserRole` con `LIDER` y `ACTIVISTA` + `lider_id` self-FK en `users`.
3. Cifrado en reposo de `clave_elector` (Fernet) + `clave_masked` derivado (enfoque B).
4. Consentimiento obligatorio por registro (con timestamp + versión de aviso) — baseline no-negociable de Fase 7.
5. Campo `area` (área/programa de activismo) en el registro.
6. Login por **teléfono o email**.
7. **Fundamento multitenant + superadmin**: bypass de scoping para superadmin y selección de base; corrección del contexto de campaña del superadmin.
8. API de captura: `POST/GET/PUT/DELETE /registros`, `GET /perfil`, con scope por rol.
9. Frontend: módulo de captura adaptado de la semilla, conectado a la API.
10. Auditoría en alta/edición/borrado de registros.
11. Pruebas (modelo, auth, permisos, API, build frontend).

### Fuera de alcance (sub-proyectos siguientes)
- **SPA-2 · Consola superadmin + admin:** listar/cambiar entre bases en la UI, alta de organizaciones/usuarios, dashboards consolidados cross-base con columna "base", `/admin/registros`, métricas, **revelar clave en claro** (con audit), consola de auditoría, catálogo administrable de áreas.
- **SPA-3 · Offline PWA:** cola IndexedDB + sync + idempotencia plena por `client_uuid` + service worker/manifest.
- **SPA-4 · Compliance + export + deploy:** ARCO (hard-delete por solicitud del titular), política de retención/purga, aviso de privacidad versionado con registro formal de aceptación, export Excel/CSV con scope, security review, QA, promoción QA→beta→prod.

> Nota: SPA-1 NO incluye ninguna ruta que devuelva la clave de elector en claro. El descifrado/revelar es exclusivo de SPA-2 y siempre con auditoría. Esto mantiene la superficie de exposición en cero durante SPA-1.

## 3. Modelo de datos

### 3.1 Tabla nueva: `registros`
Mixins: `UUIDMixin` + `TenantMixin` (organization_id NOT NULL) + `CampaignMixin` (campaign_id NOT NULL) + `AuditMixin` (created_at/updated_at/deleted_at/created_by/updated_by — soft-delete incluido).

| Columna | Tipo | Notas |
|---|---|---|
| `id` | UUID (str 36) | PK (mixin) |
| `organization_id` | FK organizations | NOT NULL, derivado de la base (mixin) |
| `campaign_id` | FK campaigns | NOT NULL, derivado de la base (mixin) |
| `activista_id` | FK users.id | quién capturó (NOT NULL) |
| `nombre_completo` | String(255) | requerido |
| `seccion` | String(20) | nullable |
| `direccion` | String(500) | nullable |
| `colonia` | String(255) | nullable |
| `telefono` | String(40) | nullable |
| `area` | String(120) | nullable — área/programa de activismo |
| `clave_elector_enc` | LargeBinary | nullable — ciphertext Fernet, nunca en claro |
| `clave_masked` | String(20) | nullable — p.ej. `****-1234`, lo que ven los listados |
| `consentimiento` | Boolean | NOT NULL, **debe ser true para insertar** |
| `consentimiento_at` | DateTime(tz) | sellado al guardar |
| `aviso_version` | String(40) | versión del aviso aceptado (constante por ahora, p.ej. `"v1"`) |
| `client_uuid` | String(64) | nullable — idempotencia; uso pleno en SPA-3 |
| `lat` | Float | nullable |
| `lng` | Float | nullable |

**Índices:** `(campaign_id, activista_id)`, `(campaign_id, seccion)`, **unique** `(campaign_id, client_uuid)` (idempotencia; permite NULLs múltiples).

### 3.2 Cambios a `users`
- `UserRole` gana `LIDER = "lider"` y `ACTIVISTA = "activista"` (enum `user_role`).
- Nueva columna `lider_id`: self-FK `users.id`, nullable, index. Define la estructura líder→activista. Un activista apunta a su líder; un líder tiene `lider_id = NULL`.

### 3.3 Migración Alembic 0008
Sigue los patrones endurecidos de 0007 / [[prod-recovery-alembic-enums]]:
- Helpers `_table_exists` / `_index_exists`; sin `try/except` de control de flujo.
- Extender el enum PG `user_role` con los **NOMBRES en mayúscula** (`LIDER`, `ACTIVISTA`) vía `ALTER TYPE ... ADD VALUE` (PG); en SQLite el enum es VARCHAR, sin acción.
- `clave_elector_enc` como `LargeBinary` (PG `BYTEA`, SQLite `BLOB`).
- `client_uuid` unique compuesto con `campaign_id`, dialect-safe.
- Crear tabla + índices + `users.lider_id` idempotentemente. Downgrade simétrico (drop tabla + columna; los valores de enum no se eliminan, consistente con migraciones previas).

## 4. Cifrado y baseline de cumplimiento (Fase 7, parte no-negociable, desde el día 1)

### 4.1 `app/core/crypto.py`
- `encrypt_clave(plain: str) -> bytes` — Fernet sobre `FERNET_KEY`.
- `decrypt_clave(ct: bytes) -> str` — usado SOLO por el reveal de SPA-2; no se llama en SPA-1.
- `mask_clave(plain: str) -> str` — devuelve `****-<últimos 4>` (p.ej. `****-1234`); si la clave es más corta, enmascara lo que haya.
- La clave Fernet se lee de `settings.FERNET_KEY` (env). **Si falta o es inválida, la app falla al arrancar** (no hay fallback a texto en claro). Se documenta en `.env.example` y se configura en Railway. **Nunca** en el repo.
- `cryptography` se añade a `backend/requirements.txt`.

### 4.2 Reglas de cumplimiento aplicadas en SPA-1
- **Enfoque B (enmascarado por defecto):** el servicio cifra la clave a `clave_elector_enc` y calcula `clave_masked` al escribir. Los listados y lecturas **nunca descifran** — solo exponen `clave_masked`. Ninguna respuesta de SPA-1 incluye `clave_elector_enc` ni la clave en claro.
- **Consentimiento obligatorio:** el servicio rechaza con `422` cualquier alta/edición con `consentimiento != true`. Al guardar, sella `consentimiento_at` (ahora) y `aviso_version`.
- **Validación de clave:** si se envía clave de elector, se valida formato INE (18 caracteres alfanuméricos en mayúscula) antes de cifrar; vacía/omitida es válida (la clave es opcional en la semilla).
- **Auditoría:** alta, edición y borrado de registro emiten `AuditLog` (reusa `audit_service`) con `action`, `entity_type="registro"`, `entity_id`, `organization_id` objetivo, y `actor_id`. Acciones del superadmin sobre una base ajena registran la org objetivo.
- **Sin datos personales en query strings ni logs** en claro (búsqueda por nombre va en query param pero no se loguea el valor; revisar que no haya logging de payloads).

## 5. Autenticación: login por teléfono o email

- `authenticate_user(db, identifier, password)` resuelve al usuario por `email` **o** `phone` (un solo campo "identificador" en el form de login). Se mantiene `verify_password` + chequeo `is_active`/`deleted_at`.
- `phone` debe ser **único** (constraint nueva o validación a nivel servicio; dado "una o pocas campañas" basta unicidad global como el email — se añade unique index en `users.phone` permitiendo NULL).
- JWT, scoping, `must_change_password` y RBAC **sin cambios**.
- Schema de login acepta `identifier` (back-compat: si el front actual manda `email`, se acepta como identificador).

## 6. Fundamento multitenant + superadmin

Hoy `scoped_query` filtra `organization_id == ctx.organization_id`; para un superadmin (`organization_id = NULL`) eso devuelve cero filas en tablas tenant-estrictas. Además `get_campaign_context` arma el contexto del superadmin con `organization_id = None` aun cuando seleccionó una campaña. Se corrige así:

### 6.1 Selección de base (solo superadmin)
- El superadmin elige la base activa con el header **`X-Campaign-Id`** (la campaña ya determina su `organization_id`). Operar "dentro de una base" = enviar `X-Campaign-Id`.
- **Corrección en `get_campaign_context`:** cuando el actor es superadmin y selecciona una campaña, el `CampaignContext` adopta `organization_id = campaign.organization_id` (la org de la base), no `None`. Para usuarios normales no cambia nada (su org ya se valida igual a la de la campaña).

### 6.2 Bypass de scoping para superadmin
- `scoped_query(model, ctx)` gana: **si `ctx.is_superadmin` y `ctx.organization_id is None` → se omiten los filtros de `organization_id` y `campaign_id`** (modo consolidado: ve todas las bases). Si el superadmin seleccionó base (`organization_id` poblado vía 6.1) → filtro normal con esa org/campaña.
- Para roles no-superadmin: **comportamiento idéntico al actual** (encerrados en su org/campaña). El bypass es estrictamente aditivo y gated por `is_superadmin`.

### 6.3 Escrituras del superadmin
- Las escrituras derivan `organization_id`/`campaign_id` de la base seleccionada (header), **nunca** del body (Golden Rule #2).
- Si el superadmin intenta una escritura **sin** base seleccionada → `400 "selecciona una base"`.

### 6.4 Auditoría cross-tenant
- Toda lectura/escritura del superadmin sobre una base ajena emite `AuditLog` con la `organization_id` objetivo, dejando trazado el acceso del operador a datos de clientes.

### 6.5 Frontera SPA-1 / SPA-2
SPA-1 entrega el **fundamento correcto a nivel de scoping y contexto** + la capacidad del superadmin de **operar dentro de cualquier base** (vía `X-Campaign-Id`), cubierto por pruebas (incluida una que demuestra que el modo consolidado a nivel query devuelve filas de múltiples orgs). La **UI/endpoint consolidado con columna "base"** (`/admin/registros` agregando todas las bases) es de SPA-2.

## 7. API de captura

Todas las respuestas son Pydantic; **nunca** ORM crudo ni `clave_elector_enc`/clave en claro. Listas paginadas con shape `{items, total, limit, offset}`. Errores con envelope `{ "error": { "message", "status" } }`.

Helper de scope por rol `registro_scope(ctx)` sobre `scoped_query`:
- **activista** → solo registros con `activista_id == ctx.user.id` (propio).
- **lider** → registros cuyos `activista_id` están en `{usuarios con lider_id == ctx.user.id}` (su estructura) **más los propios** (`activista_id == ctx.user.id`), ya que un líder también puede capturar.
- **admin** → toda la campaña (scope de campaña estándar).
- **superadmin** → según base seleccionada / consolidado (sección 6).

| Método | Endpoint | Rol mínimo | Notas |
|---|---|---|---|
| POST | `/api/registros` | activista+ | Requiere `X-Campaign-Id`. Valida consentimiento (422 si false) y clave (formato INE). Cifra + enmascara. Idempotente por `(campaign_id, client_uuid)`: si el `client_uuid` ya existe, devuelve el registro existente (200) en vez de duplicar. Escribe audit. |
| GET | `/api/registros/mios` | activista+ | Requiere `X-Campaign-Id`. Paginado; búsqueda por `q` (nombre/sección). Scope por rol. Devuelve `clave_masked`. |
| GET | `/api/registros/{id}` | activista+ | Scope por rol; 404 fuera de scope. |
| PUT | `/api/registros/{id}` | activista+ (scope) | Edita; re-cifra/re-enmascara si cambia la clave; revalida consentimiento. Audit. |
| DELETE | `/api/registros/{id}` | activista+ (scope) | Soft-delete (`deleted_at`). Audit. |
| GET | `/api/perfil` | activista+ | Datos del usuario: nombre, rol, líder (nombre), sección, organización/base. |

Registro de routers en `main.py` con prefijo `/api`, siguiendo el patrón existente.

## 8. Frontend: módulo de captura

- Adaptar `docs/registro-activista.jsx` → `frontend/src/modules/captura/CapturaPage.tsx` (React/TS), conectado a la API vía `apiClient` + el patrón `useAsync`/`DataState` existente. Cliente API en `frontend/src/api/registros.ts`.
- **Se conserva** de la semilla: aviso de privacidad + checkbox de consentimiento obligatorio, validación de clave 18-char con hint, UX móvil (max-width 640, grid responsive), lista con editar/borrar, estilos.
- **Cambia:**
  - El bloque "Datos del activista" (header capturado a mano) se reemplaza por el **perfil del usuario logueado** (`GET /perfil`): nombre del activista, su líder, sección.
  - Persistencia `localStorage` → **llamadas API** (la cola offline real es SPA-3; en SPA-1 la app requiere conexión).
  - Se añade el campo **`area`** (área/programa) al formulario.
  - Se **quitan** los botones de export (Excel/CSV) — el export con scope llega en SPA-4.
  - Estado vacío → "Aún no hay registros…" (mismo copy de la semilla).
- Registrar el módulo en `frontend/src/modules/registry.ts` con roles `ACTIVISTA`/`LIDER`/`ADMIN` (y superadmin pasa siempre).
- `LoginPage`: el campo acepta **identificador** (teléfono o email) en vez de solo email.

## 9. Pruebas (Definición de Hecho)

- **Modelo / migración:** constraints (consentimiento NOT NULL, FKs); scope por `campaign_id`; **la clave se guarda cifrada** (assert en DB que `clave_elector_enc` ≠ texto en claro y que `clave_masked` es la máscara); unique `(campaign_id, client_uuid)`. Smoke de migración 0007→0008 en PostGIS.
- **Cripto:** round-trip `encrypt`/`decrypt`; `mask_clave` produce `****-1234`; arranque falla sin `FERNET_KEY`.
- **Auth:** login por teléfono y por email resuelven al mismo usuario; identificador inválido → 401.
- **Permisos (matriz del pack):** activista NO ve registros de otro; líder ve solo su estructura; admin ve toda la campaña; superadmin sin base ve consolidado (filas de ≥2 orgs); superadmin con base ve solo esa base; escritura de superadmin sin base → 400.
- **API:** ciclo crear→listar→editar→borrar; consentimiento false → 422; idempotencia: dos POST con el mismo `client_uuid` → un solo registro.
- **Auditoría:** alta/edición/borrado generan `AuditLog`.
- **Frontend:** `npm run build` verde.
- Suite backend completa verde (sin regresiones en los módulos existentes; especial atención al cambio en `scoped_query`).

## 10. Riesgos y mitigaciones

- **Cambio en `scoped_query` (chokepoint global)** → riesgo de regresión multitenant. Mitigación: el bypass es aditivo y gated por `is_superadmin`; se corre la suite completa y se añaden tests de no-regresión para roles normales.
- **Datos sensibles** → cifrado + enmascarado + consentimiento desde el día 1; reveal diferido a SPA-2 con audit. La validación completa de compliance es SPA-4 (bloqueante para prod).
- **Captura offline duplicada** → columna `client_uuid` + unique `(campaign_id, client_uuid)` desde ahora; lógica de sync en SPA-3.
- **`FERNET_KEY` mal gestionada** → fail-fast al arrancar; documentada en `.env.example` y Railway; rotación de clave se considera en SPA-4.
- **Crecimiento multi-campaña** → el modelo ya es org+campaign-scoped; el rol en `User` (no por-campaña) es una simplificación consciente acorde a "una o pocas campañas" (ADR-1); migrar a rol por-campaña queda como puerta abierta.

## 11. Trabajo pendiente previo (no bloqueante para diseñar, sí para deploy)

El branch `feat/sp0b2b-tidy-facts` está construido y verificado pero su PR no se ha mergeado. SPA-1 se construirá sobre `main`; conviene mergear SP0b-2b antes o trabajar SPA-1 en su propia rama desde `main` para evitar divergencia.
