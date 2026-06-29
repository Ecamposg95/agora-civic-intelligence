# RBAC v2 — Redefinición de Roles y Permisos (plataforma completa)

**Fecha:** 2026-06-29
**Estado:** Diseño aprobado (brainstorming). Pendiente: plan de implementación.
**Alcance:** Toda la plataforma `agora-civic-intelligence` (no solo el módulo de activistas).

## 1. Objetivo

Redefinir **quién ve qué** y **quién puede hacer qué** en toda la plataforma, pasando de un modelo *default-open* (hoy la mayoría de módulos de inteligencia son visibles para cualquier usuario autenticado) a un modelo **default-deny** con una matriz de 9 roles explícita, aplicada **tanto en frontend (menú/ruta) como en backend (endpoints de datos)**.

## 2. Problema actual

- En `frontend/src/modules/registry.ts`, los módulos sin campo `roles:` son visibles para **cualquier autenticado** → un `activista` o `viewer` ve hoy casi toda la inteligencia electoral (mapas, analítica, resultados, padrón, etc.).
- Muchos endpoints de inteligencia en el backend **solo filtran por tenant** (`scoped_query`), no por rol → la restricción de menú en frontend no está respaldada por el backend.
- Solo existen 6 roles (`SUPERADMIN/ADMIN/ANALYST/VIEWER` del spine + `LIDER/ACTIVISTA`); falta granularidad de campo (coordinación) y de captura (capturista de oficina) y de invitado externo.

## 3. Conjunto de roles (9)

| Rol (enum NAME) | valor | Quién es | Alcance de datos |
|---|---|---|---|
| `SUPERADMIN` | superadmin | Operador de plataforma | Cross-tenant (consolidado / por base) |
| `ADMIN` | admin | Dueño de campaña/org | Toda su campaña |
| `COORDINADOR` 🆕 | coordinador | Coordina varios líderes | Su sub-estructura: sus líderes + los activistas de esos líderes |
| `LIDER` | lider | Jefe de activistas | Su estructura: sus activistas (+ lo propio) |
| `ACTIVISTA` | activista | Captura en campo | Solo lo que él capturó |
| `CAPTURISTA` 🆕 | capturista | Digitaliza formatos (oficina) | Solo lo que él capturó (sin estructura, sin líder) |
| `ANALYST` | analyst | Analista de inteligencia | Lectura de inteligencia de su campaña; sin datos personales sensibles |
| `VIEWER` | viewer | Consulta operativa básica | Lectura limitada |
| `CONSULTA` 🆕 | consulta | Invitado externo / directivo | Solo tableros y reportes ejecutivos agregados |

**Jerarquía de estructura de campo:** `Campaña → COORDINADOR → LIDER → ACTIVISTA`. `CAPTURISTA` es plano (captura sin estructura).

## 4. Principio rector: default-deny

- Cada módulo del frontend declara explícitamente su lista `roles:` (ya no hay módulos sin `roles`).
- Cada endpoint de datos del backend se protege con `require_roles(...)` (o un dependency equivalente), incluso los de inteligencia que hoy solo están tenant-scoped.
- Lo no concedido explícitamente, se niega.

## 5. Matriz de VISIBILIDAD (módulos × roles)

SA=SUPERADMIN AD=ADMIN CO=COORDINADOR LI=LIDER AC=ACTIVISTA CP=CAPTURISTA AN=ANALYST VI=VIEWER CN=CONSULTA. ✅=acceso · 👁️=solo lectura · ❌=sin acceso.

| Módulo (key registry) | SA | AD | CO | LI | AC | CP | AN | VI | CN |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `dashboard` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `maps`, `analytics`, `resultados`, `padron`, `territorios`, `ieem`, `worldbank`, `economia`, `denue`, `banxico`, `demografia`, `indice` (inteligencia) | ✅ | ✅ | ✅ | 👁️ | ❌ | ❌ | ✅ | 👁️ | ❌ |
| `sources` (fuentes de datos) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 👁️ | ❌ | ❌ |
| `busqueda` (búsqueda global) | ✅ | ✅ | ✅ | 👁️ | ❌ | ❌ | ✅ | 👁️ | ❌ |
| `ai-analyst` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `captura` (captura activistas) | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `admin-dashboard`, `admin-registros` (consola) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `admin-estructura` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `reportes` (ejecutivos) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `auditoria`, `historial` (gobernanza) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `users`, `campaigns`, `organization`, `configuracion` (admin) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `organizaciones` (cross-tenant) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Notas:
- La consola admin la ven CO y LI pero **con alcance**: CO ve su sub-estructura, LI ve su estructura (se aplica vía `_role_scoped`, no solo por menú).
- `reportes` es agregado (sin PII), por eso lo ven AN/VI/CN.

## 6. Matriz de ACCIONES sensibles (× roles)

| Acción | SA | AD | CO | LI | AC | CP | AN | VI | CN |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Capturar / editar registro | ✅ | ✅ | ❌ | ✅(estr) | ✅(propio) | ✅(propio) | ❌ | ❌ | ❌ |
| Borrar registro (soft) | ✅ | ✅ | ❌ | ✅(propio) | ✅(propio) | ✅(propio) | ❌ | ❌ | ❌ |
| **Revelar clave de elector** (descifrar, auditado) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Exportar registros (enmascarado) | ✅ | ✅ | ✅(sub) | ✅(estr) | ❌ | ❌ | agregados | ❌ | ❌ |
| Exportar con clave revelada (auditado) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ARCO hard-delete (auditado) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Ver bitácora de auditoría | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Alta de usuarios | ✅ todos | ✅ coord/líder/activista/capturista | ✅ líder/activista (su sub-estructura) | ✅ activista (su estructura) | ❌ | ❌ | ❌ | ❌ | ❌ |

**Decisiones cerradas (defaults aprobados):**
- COORDINADOR es **supervisor**: NO captura ni edita registros; sí ve y exporta su sub-estructura.
- COORDINADOR **sí** da de alta líderes y activistas dentro de su sub-estructura.
- ANALYST exporta solo **agregados** (reportes), nunca el listado granular con PII.

## 7. Modelo de datos

- **Enum `UserRole`** (`backend/app/models/user.py`): añadir `COORDINADOR = "coordinador"`, `CAPTURISTA = "capturista"`, `CONSULTA = "consulta"`. Migración Alembic que añade los valores al enum PG con el patrón endurecido (NOMBRES en mayúscula + `ALTER TYPE ... ADD VALUE` en `autocommit_block`; ver [[prod-recovery-alembic-enums]]). SQLite = VARCHAR, sin DDL.
- **`User.coordinador_id`** self-FK (`users.id`, `ondelete=SET NULL`, index, nullable): un `LIDER` apunta a su `COORDINADOR`. Migración para la columna. (Análogo a `lider_id`.)
- Sin tablas nuevas.

## 8. Scoping (`backend/app/services/registro_service.py::_role_scoped` y `app/core/scoping.py`)

`_role_scoped(ctx)` se extiende por rol (sobre el `scoped_query` base que aplica tenant + campaña + soft-delete):
- `SUPERADMIN`: bypass/consolidado (sin cambios).
- `ADMIN`: alcance de campaña completo (sin cambios).
- `COORDINADOR` 🆕: registros cuyo `activista_id ∈` (activistas cuyo `lider_id ∈` (líderes cuyo `coordinador_id == ctx.user.id`)) — subconsulta de 2 niveles. Incluye registros capturados directamente por sus líderes.
- `LIDER`: propio + activistas con `lider_id == ctx.user.id` (sin cambios).
- `ACTIVISTA`: solo `activista_id == ctx.user.id` (sin cambios).
- `CAPTURISTA` 🆕: solo `activista_id == ctx.user.id` (igual que activista; sin estructura).
- `ANALYST`/`VIEWER`/`CONSULTA`: NO acceden a registros granulares → `_role_scoped` devuelve conjunto vacío para estos roles (defensa en profundidad; el router ya los bloquea con `require_roles`).

## 9. Backend — gating por endpoint

- `require_roles` (en `backend/app/dependencies.py`) sin cambios de firma; se actualizan las listas de roles en los routers:
  - `routers/registros.py` (captura): `ACTIVISTA, CAPTURISTA, LIDER, ADMIN` (+SA auto). (CO fuera de captura.)
  - `routers/admin.py`: lista/métricas/estructura → `ADMIN, COORDINADOR, LIDER` (+SA); revelar-clave/auditoría → `ADMIN` (+SA).
  - `routers/exports.py`: export → `ADMIN, COORDINADOR, LIDER` (+SA); reveal-export → `ADMIN` (+SA).
  - `routers/arco.py`: `ADMIN` (+SA) (sin cambios).
  - `routers/users.py`: alta/edición → `ADMIN, COORDINADOR, LIDER` (+SA) con **validación de alcance** (un COORDINADOR solo crea líder/activista en su sub-estructura; un LIDER solo activista en su estructura; ADMIN cualquiera de su campaña). Reusar/extender `_validate_lider` + nueva `_validate_coordinador`.
  - `routers/reports.py`: `ADMIN, COORDINADOR, LIDER, ANALYST, VIEWER, CONSULTA` (+SA) — agregados sin PII.
  - **Inteligencia** (maps/analytics/resultados/padron/territorios/ieem/worldbank/economia/denue/banxico/demografia/indice/busqueda): añadir `require_roles(ADMIN, COORDINADOR, LIDER, ANALYST, VIEWER)` (+SA) a los endpoints de lectura que hoy solo están tenant-scoped. (LI/VI = lectura.)
  - `sources`: `ADMIN, ANALYST` (+SA).
  - `ai-analyst`: `ADMIN, COORDINADOR, ANALYST` (+SA).
  - Admin/cross-tenant (users/campaigns/organization/configuracion/organizaciones/auditoria/historial): `ADMIN` (+SA), `organizaciones` solo SA.

## 10. Frontend

- `frontend/src/types/auth.ts`: `UserRole` += `"coordinador" | "capturista" | "consulta"`.
- `frontend/src/modules/registry.ts`: poner `roles:` **explícito en TODOS los módulos** según la matriz §5 (roles en minúscula, p.ej. `["superadmin","admin","coordinador","lider","analyst","viewer"]` para inteligencia). Ningún módulo sin `roles`.
- Verificar que el guard de ruta + el filtrado de menú usan `roles` (ya existe el patrón; confirmar que un rol sin acceso recibe 403/redirect, no solo menú oculto).
- Donde el frontend muestra acciones (botón revelar-clave, exportar, alta usuarios), gatear por rol del usuario (ya hay patrón en `AdminRegistrosPage`).

## 11. Seed / demo

- Extender el demo-seed (bootstrap `_seed_demo_activists` + `scripts/local_seed.py`) opcionalmente con un `COORDINADOR` y un `CAPTURISTA` demo (env-gated, idempotente) para poder probar la matriz en prod. Ligar: coordinador → (líder lucy) → activista. Passwords por env.

## 12. Pruebas

- Backend: por cada rol nuevo y por la matriz — tests de `_role_scoped` (CO ve 2 niveles, CP solo propio, AN/VI/CN vacío), tests de `require_roles` por endpoint (403 para roles no permitidos en captura/consola/inteligencia/admin), test de alta-de-usuario con validación de alcance (CO no crea fuera de su sub-estructura). Migración enum + columna `coordinador_id` con round-trip SQLite.
- Frontend: `npm run build` verde; (si vitest) prueba del filtrado de registry por rol.

## 13. Compatibilidad y despliegue (IMPORTANTE — app en prod con usuarios)

- **Cambio de comportamiento visible:** pasar a default-deny **oculta/bloquea** módulos que hoy ven todos. Comunicar/validar antes de desplegar. Los usuarios existentes con rol `VIEWER`/`ANALYST` mantienen acceso de lectura a inteligencia según la matriz.
- La migración del enum es aditiva (no rompe datos). `coordinador_id` es nullable (no rompe filas existentes).
- Reusar patrón de migración endurecido (autocommit_block para ADD VALUE). Reconciliar numeración Alembic sobre el head vigente.
- Desplegar a Railway tras verde local + revisión; smoke de login por cada rol.

## 14. Fuera de alcance

- Permisos a nivel de campo individual / por-columna (más allá de masked-vs-reveal de la clave, ya existente).
- Roles configurables por el usuario (RBAC dinámico/custom roles): este diseño es un set fijo de 9.
- Rol AUDITOR (descartado en brainstorming; auditoría la ven SA/AD).
- Refactor de RBAC dinámico/políticas (ABAC): YAGNI.
