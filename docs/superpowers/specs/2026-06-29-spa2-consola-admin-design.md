# SPA-2 · Consola Admin / Superadmin — Design

- **Fecha:** 2026-06-29
- **Programa:** AGORA — Plataforma de Captura y Gestión de Activistas (vertical dentro de `agora-civic-intelligence`, stack Atlas)
- **Sub-proyecto:** SPA-2 (segunda rebanada del Task Pack Maestro de Activistas)
- **Cubre del pack:** Fase 5 (API admin) + Fase 6 (dashboard admin) + la parte de consola de la visibilidad cross-tenant del superadmin (la columna "base" / modo consolidado)
- **Construye sobre:** SPA-1 (rama `feat/spa1-captura-activistas`, **ya implementada, no mergeada a main**)
- **Estado:** diseño, pendiente de ejecución del plan `docs/superpowers/plans/2026-06-29-spa2-consola-admin.md`

---

## 1. Objetivo y encuadre

SPA-1 entregó la **captura** (un activista registra personas) y el **fundamento multitenant** (bypass de scoping del superadmin, adopción de org de la base vía `X-Campaign-Id`). SPA-2 entrega la **consola de gestión**: que un **admin** (responsable de campaña) y el **superadmin** (operador de plataforma) puedan **ver, medir, gobernar y auditar** lo capturado, gestionar la **estructura líder→activista** y, cuando sea estrictamente necesario, **revelar la clave de elector en claro con auditoría obligatoria**.

**Encuadre confirmado (consistente con SPA-1 implementado):**
- No se introducen tablas nuevas del pack (`campania/usuario/registro/audit_log`). SPA-1 **reusó el spine Atlas**: `Organization` (= "base"/tenant), `Campaign`, `User` (con `UserRole` que ya incluye `LIDER`/`ACTIVISTA`, self-FK `lider_id`, `seccion`), `Registro` (tabla `registros`, `clave_elector_enc` Fernet + `clave_masked`), `AuditLog`, `scoped_query` con bypass de superadmin, y `crypto.decrypt_clave` (ya existe, no usado aún).
- SPA-2 es **mayormente lectura + servicios/routers admin nuevos**: no requiere migración de esquema. La única extensión de modelo es a nivel de **schemas/servicio de usuarios** para exponer la asignación de estructura (`lider_id`, `seccion`) que el modelo `User` **ya soporta** en columnas existentes.

## 2. Alcance

### En alcance (SPA-2)

**Fase 5 — API admin (`/api/admin/*` + extensión de `/api/users`):**
1. `GET /admin/registros` — listado de campaña con filtros (líder, activista, sección, fecha) + búsqueda + paginado; **clave enmascarada por defecto**; incluye columna **`organization_id` + `organization_name` ("base")** para el modo consolidado del superadmin.
2. `GET /admin/metricas` — totales por líder/activista/sección + avance diario; respeta scope por rol.
3. `POST /admin/registros/{id}/revelar-clave` — descifra `clave_elector_enc` con `crypto.decrypt_clave` y **emite `AuditLog` obligatorio** (`action="registro.reveal_clave"`, org objetivo). **Solo admin/superadmin** (nunca líder ni activista).
4. `GET /admin/auditoria` — bitácora filtrable (delegando en `audit_service.list_events`, tenant-scoped, consolidada para superadmin).
5. `GET /admin/estructura` — árbol Líder→Activistas con conteos de registros (subárbol propio para líder).
6. CRUD de usuarios con **asignación de estructura**: extender `/api/users` (`UserCreate`/`UserUpdate` + `users_service`) para aceptar y **validar** `lider_id` (debe referenciar un usuario `LIDER` de la misma org; sin auto-referencia) y `seccion` — habilita alta de líderes/activistas y la asignación líder→activista.
7. **Dependencia de contexto admin** (`get_admin_context`/`AdminCtx`) que permite al superadmin operar en **modo consolidado** (sin `X-Campaign-Id` → org/campaign `None`) o **dentro de una base** (con header → adopta org), y obliga a admin/líder a tener una campaña seleccionada.

**Fase 6 — Dashboard admin (frontend):**
8. Módulo admin (registrado en `frontend/src/modules/registry.ts`), con **tablero** (total registros, avance diario con `recharts`, top activistas, cobertura por sección), **tabla de registros** con filtros/búsqueda/paginación + columna "base" + botón **revelar clave** (solo admin), y **gestión de estructura** (árbol Líder→Activistas con conteos + alta/edición de usuarios con asignación de líder y sección).
9. **Selector de base consolidada** para superadmin: opción "Todas las bases (consolidado)" que limpia el `X-Campaign-Id` activo (reusa `campaignStore`); con base seleccionada el filtrado es normal.

### Fuera de alcance (sub-proyectos siguientes)
- **SPA-3 · Offline PWA:** cola IndexedDB + sync + service worker/manifest + idempotencia plena por `client_uuid`.
- **SPA-4 · Compliance + export + deploy:** ARCO (hard-delete por solicitud del titular), retención/purga, aviso de privacidad versionado con aceptación formal, **export Excel/CSV con scope**, security review, QA, promoción QA→beta→prod.
- Catálogo administrable de **áreas** (mencionado en SPA-1 como SPA-2; se **difiere**: en SPA-2 `area` sigue siendo texto libre — ver §10 preguntas abiertas).

## 3. Cambios de datos / modelo

**Ninguna tabla ni columna nueva. No hay migración Alembic en SPA-2.**

- `Registro`, `User.lider_id`, `User.seccion`, `User.role` (LIDER/ACTIVISTA), `clave_elector_enc`, índices `(campaign_id, activista_id)` y `(campaign_id, seccion)` ya existen (Alembic head `0008` en la rama SPA-1).
- Las métricas usan `func.date(Registro.created_at)` (dialect-safe PG/SQLite) y agregaciones `count/group_by`; los índices existentes cubren los filtros por activista/sección. No se requiere índice nuevo para el alcance previsto (volúmenes "una o pocas campañas", ADR-1).
- **Nota de integración (numeración Alembic):** la rama SPA-1 tiene head `0008`; la rama `feat/sp0b2b-tidy-facts` tiene `0007` sin mergear (dos heads cruzados). SPA-2 **no añade migración**, así que no agrava el problema; la reconciliación de heads `0007`/`0008` se resuelve al integrar SPA-1 + SP0b-2b a `main` (fuera de SPA-2). Si una decisión futura (p. ej. catálogo de áreas) exigiera migración, su `down_revision` sería `"0008"`.

## 4. Contexto admin y modo consolidado

Hoy `get_campaign_context` **exige** `X-Campaign-Id` (400 si falta) y adopta `organization_id = campaign.organization_id` para superadmin. Eso sirve a un admin (siempre dentro de su campaña) y a un superadmin **con base seleccionada**, pero **no** al superadmin en **modo consolidado** (sin base, viendo todas las orgs).

Se añade en `backend/app/dependencies.py`:

```python
def get_admin_context(db, ctx: Tenant, x_campaign_id: Optional[str] = Header(None)) -> CampaignContext:
    # Superadmin sin base → modo consolidado: org/campaign None (scoped_query hace bypass).
    if ctx.is_superadmin and not x_campaign_id:
        return CampaignContext(user=ctx.user, organization_id=None, role=ctx.role, campaign_id="")
    # En cualquier otro caso se requiere base/campaña (reusa la validación existente,
    # que para admin/líder verifica membership y org, y para superadmin adopta la org de la base).
    return get_campaign_context(db, ctx, x_campaign_id)

AdminCtx = Annotated[CampaignContext, Depends(get_admin_context)]
```

- **Admin/líder:** siempre requieren `X-Campaign-Id` (campaña activa); 400 si falta (comportamiento heredado).
- **Superadmin sin base:** `organization_id=None`, `campaign_id=""` → `scoped_query` retorna la vista consolidada (todas las orgs/campañas), filas etiquetadas con su `organization_id`/`organization_name`.
- **Superadmin con base:** filtrado normal por esa org/campaña.

El scope por rol dentro de los servicios reusa **`registro_service._role_scoped(ctx)`** (ya implementado): activista→propios, líder→su estructura + propios, admin→campaña, superadmin→consolidado/base. SPA-2 no duplica esa lógica; la consume.

## 5. Superficie de API

Convenciones heredadas (Golden Rules de `docs/architecture.md`): respuestas Pydantic (nunca ORM ni `clave_elector_enc`/clave en claro salvo el endpoint de reveal), listas `{items,total,limit,offset}` (schema `Page[T]`/`schemas/admin`), errores `{ "error": { "message", "status" } }`, RBAC en la capa API vía `require_roles` (superadmin auto-pasa), auditoría en operaciones sensibles.

Router nuevo `backend/app/routers/admin.py` con `APIRouter(prefix="/admin", tags=["admin"])`, registrado en `app/main.py::_register_routers`.

| Método | Endpoint | Rol mínimo | Notas |
|---|---|---|---|
| GET | `/api/admin/registros` | ADMIN, LIDER | `AdminCtx`. Filtros query: `q`, `lider_id`, `activista_id`, `seccion`, `since`, `until`, `limit`, `offset`. Scope por rol (líder→su estructura). Devuelve `AdminRegistroRead` con `organization_id`+`organization_name` (base) y `activista_nombre`; **clave enmascarada**. |
| GET | `/api/admin/metricas` | ADMIN, LIDER | `AdminCtx`. Devuelve `MetricsRead`: `total`, `por_lider[]`, `por_activista[]`, `por_seccion[]`, `avance_diario[]`. Scope por rol. |
| GET | `/api/admin/estructura` | ADMIN, LIDER | `AdminCtx`. Árbol `EstructuraNode[]` (líder → activistas) con `registros_count` por nodo. Líder ve solo su subárbol. |
| POST | `/api/admin/registros/{id}/revelar-clave` | **ADMIN** (líder NO) | `AdminCtx`. Descifra con `crypto.decrypt_clave`; **siempre** `record_audit(action="registro.reveal_clave", organization_id=<org del registro>)`. 404 si fuera de scope; 422 si el registro no tiene clave. Devuelve `{ "clave_elector": "<plain>", "registro_id": "..." }`. |
| GET | `/api/admin/auditoria` | ADMIN | `Tenant`. Delega en `audit_service.list_events` (tenant-scoped, consolidada para superadmin). Filtros: `action`, `actor`, `entity_type`, `since`, `until`, paginado. |

Extensión de `/api/users` (router existente, gate `ManagerCtx = require_roles(ADMIN)`):

| Método | Endpoint | Cambio |
|---|---|---|
| POST | `/api/users` | `UserCreate` acepta `lider_id?`, `seccion?`; `users_service.create_user` valida (líder existe, rol `LIDER`, misma org; no auto-FK). |
| PATCH | `/api/users/{id}` | `UserUpdate` acepta `lider_id?` (incl. `None` para desasignar), `seccion?`; `update_user` valida igual y audita en `meta`. |

> **`/admin/auditoria` vs `/audit`:** ya existe `backend/app/routers/audit.py` (admin-gated, consolidado-aware, paginado). `/admin/auditoria` es un alias delgado para mantener la consola cohesiva y poder filtrar por `action="registro.reveal_clave"`. Ver §10 (pregunta abierta: conservar uno o ambos).

### Shapes (en `backend/app/schemas/admin.py`)

```python
class AdminRegistroRead(BaseModel):           # NO incluye clave en claro
    id, organization_id, organization_name, campaign_id, activista_id,
    activista_nombre, lider_id, lider_nombre, nombre_completo, seccion,
    colonia, area, telefono, clave_masked, consentimiento, consentimiento_at, created_at

class AdminRegistroList(BaseModel): items: list[AdminRegistroRead]; total; limit; offset

class MetricBucket(BaseModel): key: str; label: str; total: int   # genérico (lider/activista/seccion)
class DailyPoint(BaseModel): fecha: str; total: int
class MetricsRead(BaseModel):
    total: int; por_lider: list[MetricBucket]; por_activista: list[MetricBucket]
    por_seccion: list[MetricBucket]; avance_diario: list[DailyPoint]

class EstructuraNode(BaseModel):
    lider_id: str; lider_nombre: str; seccion: Optional[str]; registros_count: int
    activistas: list["EstructuraActivista"]
class EstructuraActivista(BaseModel):
    id: str; nombre: str; seccion: Optional[str]; registros_count: int

class RevelarClaveResponse(BaseModel): registro_id: str; clave_elector: str
```

## 6. Seguridad y cumplimiento

- **Reveal siempre auditado (requisito duro del pack §2/§4):** `admin_service.reveal_clave` llama `crypto.decrypt_clave(bytes(reg.clave_elector_enc))` **y** `record_audit(...)` antes del `commit`; ambos en la misma transacción. La `organization_id` del audit es la **del registro** (base objetivo), de modo que el acceso del superadmin a una base ajena queda trazado. Solo `ADMIN`/`SUPERADMIN` (gate `require_roles(UserRole.ADMIN)`, que excluye `LIDER`/`ACTIVISTA`).
- **Enmascarado por defecto:** ninguna respuesta de listado/métricas/estructura descifra; solo `clave_masked`. La clave en claro existe únicamente en la respuesta puntual de `revelar-clave`.
- **Sin PII en logs/query en claro:** la búsqueda por nombre va en `q` pero no se loguea; `meta` de audit nunca contiene la clave ni el nombre completo (solo ids).
- **RBAC:** matriz del pack §2 — admin ve scope de campaña; líder solo su estructura (vía `_role_scoped`); reveal admin-only; líder ve claves enmascaradas. Superadmin auto-pasa `require_roles` y opera por base/consolidado.
- **Cross-tenant del superadmin:** lecturas consolidadas no auditan por volumen (consistente con SPA-1 §6.4 a nivel diseño), pero **toda revelación de clave sí** audita con la org objetivo.

## 7. Frontend (Fase 6)

Stack real verificado: **React 18 + TS + Vite + Tailwind + Zustand**, patrón **`useAsync`/`DataState`** (NO TanStack Query), `recharts` **ya es dependencia** (`^2.13.3`), `apiClient` (axios) inyecta `Authorization` + `X-Campaign-Id` automáticamente. Componentes reusables existentes: `AppLayout`, `PageHeader`, `Card`, `MetricCard`, `DataTable`/`Column`, `DataState`, `SkeletonRows`, iconos en `@/components/ui/icons`. Se siguen patrones de `modules/auditoria/AuditoriaPage.tsx` (tabla server-paginada + filtros debounced + drawer) y `pages/UsersPage.tsx` (gestión).

**Cliente API:** `frontend/src/api/admin.ts` — `getAdminRegistros(params)`, `getMetricas(params)`, `getEstructura()`, `revelarClave(id)`, `getAdminAuditoria(params)`; tipos en el mismo archivo o `@/types/admin.ts`.

**Páginas (módulo `admin`):**
- `frontend/src/modules/admin/AdminDashboardPage.tsx` — **tablero**: `MetricCard`s (total registros, top activista, secciones cubiertas), **avance diario** (`recharts` `AreaChart`/`BarChart`), **top activistas** (`BarChart`), **cobertura por sección** (`BarChart`/tabla). Consume `getMetricas`.
- `frontend/src/modules/admin/AdminRegistrosPage.tsx` — tabla `DataTable` server-paginada con filtros (líder, activista, sección, fecha) + búsqueda `q` (debounce 350ms como Auditoría) + columna **"Base"** (visible/relevante en consolidado) + botón **"Revelar clave"** (solo si `role∈{admin,superadmin}`) con `window.confirm` y muestra puntual de la clave devuelta. Consume `getAdminRegistros` / `revelarClave`.
- `frontend/src/modules/admin/AdminEstructuraPage.tsx` — árbol Líder→Activistas con conteos (`getEstructura`) + alta/edición de usuarios con asignación de **líder** y **sección** (reusa `api/users`). Gate admin/superadmin.

**Registro de módulos** (`frontend/src/modules/registry.ts`, sección `administracion` o `gobernanza`):
- `admin-dashboard` (`/admin`) y `admin-registros` (`/admin/registros`): roles `["admin", "lider", "superadmin"]`.
- `admin-estructura` (`/admin/estructura`): roles `["admin", "superadmin"]`.

**Modo consolidado (superadmin):** se añade en `campaignStore` la capacidad de **limpiar** la base activa (`setActive(null)` ya persiste `null` correctamente) y en `CampaignSwitcher` una opción "Todas las bases (consolidado)" visible solo para superadmin. Sin `X-Campaign-Id`, `get_admin_context` entra en consolidado; la columna "Base" se vuelve significativa. Con base seleccionada, filtrado normal. (Ver §10: alternativa = selector de base propio dentro de las páginas admin.)

## 8. Pruebas (Definición de Hecho)

- **Contexto admin:** superadmin sin header → consolidado (org None); superadmin con header → adopta org de la base; admin sin header → 400; admin con campaña ajena → 403/404 (heredado).
- **`/admin/registros`:** admin ve toda la campaña; líder solo su estructura; activista → 403; superadmin consolidado ve filas de ≥2 orgs con `organization_name` distinto; filtros (líder/activista/sección/fecha) y `q` aplican; respuesta **nunca** incluye `clave_elector_enc` ni clave en claro.
- **`/admin/metricas`:** totales por líder/activista/sección y avance diario coherentes con los registros sembrados; scope por rol (líder solo su estructura).
- **`/admin/estructura`:** árbol con conteos correctos; líder ve solo su subárbol.
- **`revelar-clave`:** admin obtiene la clave en claro **y** se crea `AuditLog` con `action="registro.reveal_clave"` y la org del registro; líder → 403; activista → 403; registro sin clave → 422; registro fuera de scope → 404; superadmin revela en base ajena y el audit lleva la org objetivo.
- **Usuarios + estructura:** crear activista con `lider_id`+`seccion` válidos OK; `lider_id` a usuario no-LIDER o de otra org → 400; PATCH desasigna (`lider_id=None`); cambios auditados.
- **Frontend:** `npm run build` verde; gating de módulos por rol; reveal solo visible para admin/superadmin.
- **No regresiones:** suite backend completa verde (especial atención a `dependencies.py`, que ahora tiene `get_admin_context` además de `get_campaign_context`).

## 9. Riesgos y mitigaciones

- **Nuevo dependency `get_admin_context`** reusa `get_campaign_context` → bajo riesgo; el path consolidado está gated por `is_superadmin and not x_campaign_id`. Cubierto por tests.
- **Reveal de clave** = mayor superficie de exposición de SPA-2 → mitigado: admin-only, auditado siempre, clave solo en respuesta puntual (nunca en listados), org objetivo en el audit.
- **Métricas sobre volúmenes grandes** → fuera del alcance "una o pocas campañas"; si crece, añadir índice en `(campaign_id, created_at)` y/o materializar (puerta abierta, no en SPA-2).
- **UX consolidado/base** ambigua → se entrega comportamiento mínimo (limpiar base = consolidado) y se deja la UX fina como pregunta abierta (§10).

## 10. Preguntas abiertas (decisión humana)

1. **UX de "base" consolidada:** ¿opción "Todas las bases" en el `CampaignSwitcher` global (limpia `X-Campaign-Id`, afecta también captura) **o** un selector de base **propio** dentro de las páginas admin (no toca el header global)? El plan asume la primera (más simple, reusa `campaignStore`).
2. **`/admin/auditoria` vs `/audit`:** ¿conservar ambos (alias) o que la consola consuma directamente `/audit` y no se cree `/admin/auditoria`? El plan crea el alias delgado; es trivial de retirar.
3. **Catálogo de áreas:** SPA-1 lo listaba como SPA-2. El plan lo **difiere** (en SPA-2 `area` sigue texto libre) para no introducir tabla+migración en una rebanada que de otro modo no toca el esquema. ¿Confirmar diferimiento o incluirlo (añadiría modelo + Alembic `0009`)?
4. **Permiso de líder a `/admin/registros` y `/admin/metricas`:** el pack dice "líder ve solo su estructura". El plan le da acceso de **lectura** scoped. ¿Correcto, o la consola admin es exclusiva de admin/superadmin y el líder se queda solo con la vista de captura?
