# SPA-3 · Captura Offline (PWA + cola IndexedDB + sync) — Design

- **Fecha:** 2026-06-29
- **Programa:** AGORA — Plataforma de Captura y Gestión de Activistas (vertical dentro de `agora-civic-intelligence`, stack Atlas)
- **Sub-proyecto:** SPA-3 (tercera rebanada del Task Pack Maestro de Activistas)
- **Estado:** diseño — pendiente de plan de implementación
- **Construye sobre:** rama `feat/spa1-captura-activistas` (SPA-1 entregado: modelo `registros`, API CRUD con scope por rol, cifrado Fernet, `client_uuid` con idempotencia owner-scoped). SPA-2 (consola superadmin) es independiente y no es prerequisito.
- **Task Pack origen:** Fase 4 (la parte no cubierta por SPA-1) + Riesgo §7 (campo sin señal).

---

## 1. Objetivo y encuadre

Hacer que el formulario de captura de activistas sea **usable en campo sin conexión**. Hoy `CapturaPage` (`frontend/src/modules/captura/CapturaPage.tsx`) hace un `POST /api/registros` síncrono: si no hay señal, el `await createRegistro(...)` falla y el registro se pierde. SPA-3 introduce:

1. Una **PWA instalable** que carga su shell sin red (precache de assets de build).
2. Una **cola local en IndexedDB**: los registros capturados se encolan cuando no hay conexión (o cuando el POST falla por red).
3. **Sincronización automática al reconectar** + sincronización manual, con un **indicador de "pendientes por sincronizar"**.
4. **Idempotencia plena por `client_uuid`**: el cliente genera y envía `client_uuid` en cada captura, de modo que un re-sync nunca duplica (el backend ya deduplica por `client_uuid` owner-scoped desde SPA-1).
5. Una **migración de esquema** que ensancha el `UniqueConstraint` de `(campaign_id, client_uuid)` a `(campaign_id, activista_id, client_uuid)` para alinear el constraint de BD con la semántica owner-scoped del servicio.

**Lo que YA existe (SPA-1) y se reutiliza:**
- `backend/app/services/registro_service.py` → `create_registro` ya hace lookup idempotente owner-scoped vía `_role_scoped(ctx).where(Registro.client_uuid == data.client_uuid)`; si existe, devuelve la fila existente (no duplica).
- `backend/app/models/registro.py` → columna `client_uuid` (String 64, nullable) + `UniqueConstraint("campaign_id","client_uuid", name="uq_registros_campaign_client_uuid")`.
- `frontend/src/api/registros.ts` → `RegistroCreate` ya declara `client_uuid?: string` y `createRegistro(payload)` lo envía tal cual (axios serializa el payload completo). **El hueco real:** `CapturaPage` nunca genera ni pasa `client_uuid`. SPA-3 lo cablea.
- `frontend/src/api/client.ts` → `apiClient` ya inyecta `Authorization` y `X-Campaign-Id` en cada request.

---

## 2. Alcance

### En alcance (SPA-3)
1. PWA: `manifest.webmanifest` + service worker (precache del app-shell) vía **`vite-plugin-pwa`** (Workbox por debajo).
2. Cola offline en **IndexedDB** (`registro_queue`), con módulo de cola **puro y unit-testeable**.
3. Motor de sincronización (máquina de estados `queued → syncing → synced | error`) testeable con API mockeada.
4. Generación y envío de `client_uuid` por captura (idempotencia plena).
5. Detección online/offline + indicador "pendientes por sincronizar" + botón "sincronizar ahora".
6. Migración Alembic **0009**: ensanchar el unique constraint a `(campaign_id, activista_id, client_uuid)`, dialect-safe (PG/SQLite) e idempotente.
7. Pruebas: unit del módulo de cola + del motor de sync (vitest, ver §10); backend `pytest` del nuevo constraint; `npm run build` verde.

### Fuera de alcance
- **On-device encryption-at-rest** del payload en IndexedDB (incluida la clave de elector). Ver §8 — se documenta como riesgo aceptado, no se implementa.
- Background Sync API del navegador (sync diferido por el SO aunque la pestaña esté cerrada). SPA-3 sincroniza con la app abierta (evento `online` + arranque + botón). Background Sync se anota como mejora futura.
- Resolución de conflictos de edición offline (SPA-3 solo encola **altas**; no edición/borrado offline).
- Caché offline de las **lecturas** (`GET /registros/mios`): la lista puede mostrarse vacía/parcial sin red. Caché de lectura es opcional y se anota como mejora, no requisito.
- Consola consolidada superadmin (SPA-2), export/compliance/deploy (SPA-4).

---

## 3. Enfoque PWA (librería)

**Decisión:** usar **`vite-plugin-pwa`** (devDependency) — es el camino idiomático con Vite 6 y empaqueta **Workbox** (nombrado en el stack del Task Pack), evitando escribir un service worker a mano.

> No instalado hoy: `frontend/package.json` no contiene `vite-plugin-pwa` ni `workbox-*`. **Paso de instalación requerido** (ver plan Task 2).

Configuración objetivo en `frontend/vite.config.ts`:
- `registerType: "autoUpdate"` — el SW se actualiza solo cuando hay nueva build.
- `injectRegister: "auto"` — registro del SW inyectado automáticamente (sin tocar `main.tsx`, o con un import explícito de `virtual:pwa-register` si se quiere UX de "nueva versión disponible").
- `workbox.globPatterns`: precache de `**/*.{js,css,html,svg,woff2}` del `dist`. El app-shell (`index.html` + chunks React) queda disponible offline.
- **No** se cachea `POST /api/registros` (la ruta offline es la cola IndexedDB, no el SW). Opcionalmente `runtimeCaching` NetworkFirst para `GET /api/*` queda fuera de alcance (§2).
- `manifest`: `name "Ágora — Captura"`, `short_name "Ágora"`, `theme_color` alineado al tema navy, `background_color`, `display: "standalone"`, `start_url: "/"`, `icons` (192/512 + maskable).

**Activos requeridos:** iconos PWA (192×192, 512×512, maskable) en `frontend/public/`. Hoy solo existe `frontend/public/favicon.svg`. **Generar/derivar** los PNG del favicon — anotado como sub-paso (no bloqueante para `npm run build`, pero sí para una instalación PWA correcta).

**Interacción con `index.html`:** el script anti-flash de tema en `index.html` es inline y sigue funcionando offline (parte del shell precacheado). Sin cambios.

**Producción:** el backend sirve la SPA (StaticFiles + catch-all → `index.html`, ver `docs/architecture.md`). El `sw.js` y `manifest.webmanifest` generados por Workbox quedan en `dist/` y deben servirse desde la raíz; verificar que el catch-all de `main.py` no intercepte `/sw.js` ni `/manifest.webmanifest` (deben servirse como ficheros estáticos, no como `index.html`). Anotado como concern de integración (ver §9).

---

## 4. Esquema IndexedDB de la cola

Wrapper: **`idb`** (dependency, ~1 kB) sobre IndexedDB nativo. Evita IndexedDB crudo (verboso) sin el peso de Dexie.

**DB:** `agora-offline` · **version** `1` · **objectStore:** `registro_queue`.

| Campo | Tipo | Notas |
|---|---|---|
| `client_uuid` | string (UUIDv4) | **keyPath** (clave primaria del store). Generado con `crypto.randomUUID()` al capturar. |
| `campaign_id` | string | base/campaña activa al capturar (snapshot, no del store global en sync). |
| `payload` | `RegistroCreate` | cuerpo completo a enviar (incluye `nombre_completo`, `consentimiento`, `clave_elector` en claro, `client_uuid`). |
| `status` | `"queued" \| "syncing" \| "synced" \| "error"` | estado de sync (§5). Índice `by_status`. |
| `created_at` | number (epoch ms) | orden FIFO de drenado. |
| `attempts` | number | reintentos; para backoff/diagnóstico. |
| `last_error` | string \| null | último mensaje de error (sin PII). |
| `server_id` | string \| null | `id` devuelto por el backend tras sync exitoso. |

**Índices:** `by_status` (`status`), `by_created_at` (`created_at`).

**Retención:** tras `synced`, la fila se **elimina** del store (no se conserva PII en el dispositivo más de lo necesario, ver §8). El "ya capturado" se refleja recargando `listMisRegistros()` desde el servidor. Las filas `error` se conservan para reintento manual.

**Clave compuesta de unicidad lógica:** `client_uuid` es PK del store ⇒ encolar dos veces el mismo `client_uuid` es un `put` idempotente (no crea duplicados locales). Esto se alinea con el constraint de BD ensanchado (§7).

---

## 5. Máquina de estados de sync

```
            capturar (online OK)
   [no se encola] ─────────────────▶ POST 201 ─▶ recargar lista

            capturar (offline o POST falla por red)
   ─────────────────────────────────────────────▶  queued
                                                       │  drainQueue()
                                                       ▼
                                                    syncing
                                          ┌────────────┴────────────┐
                                   POST 201/200 (idempotente)   error de red / 5xx
                                          │                          │
                                          ▼                          ▼
                                       synced                      error
                                    (borrar fila)            (attempts++, retry
                                                              en próximo online
                                                              o botón manual)
```

**Reglas:**
- **Disparadores de `drainQueue()`:** (a) evento `window 'online'`; (b) arranque de la app si hay pendientes; (c) botón "sincronizar ahora"; (d) inmediatamente tras encolar si `navigator.onLine`.
- **Drenado FIFO:** procesa `queued` (y reintenta `error`) ordenado por `created_at`. Marca `syncing` antes del POST.
- **Éxito (`201` nuevo o `200`/`201` idempotente):** el backend devuelve la fila (nueva o existente por `client_uuid`). Se borra la fila local → `synced`.
- **Error distinguido:**
  - **Error de red / 5xx / timeout** → `error`, `attempts++`, se reintentará. La fila permanece.
  - **Error de validación (`4xx` no recuperable, p.ej. 422 consentimiento)** → `error` "permanente": se marca y **no** se reintenta en bucle; se expone al usuario para corrección/descarte. (En la práctica el form ya valida consentimiento antes de encolar, así que 422 no debería ocurrir; se maneja defensivamente.)
- **Concurrencia / idempotencia:** drenar dos veces en paralelo (p.ej. `online` + botón) es seguro porque (a) el `client_uuid` es PK local y (b) el backend deduplica por `client_uuid` owner-scoped. Aun así, un guard `isDraining` evita trabajo redundante.

**Testabilidad:** la lógica de cola (`enqueue/list/markStatus/remove`) y el drenado (`drainQueue(deps)` con `createRegistro` inyectado) viven en módulos **puros** separados del service worker. Los service workers son difíciles de unit-testear; SPA-3 los mantiene como un cascarón delgado de Workbox y prueba toda la lógica de negocio en `frontend/src/offline/*.test.ts`.

---

## 6. Idempotencia vía `client_uuid`

- **Generación:** `crypto.randomUUID()` en el momento de capturar (no en el momento de enviar). Así un mismo registro conserva su `client_uuid` a través de reintentos/recargas.
- **Envío:** se incluye en el `payload` (`RegistroCreate.client_uuid`) tanto en el camino online directo como en el drenado de cola. `createRegistro` ya lo serializa.
- **Backend (sin cambios de lógica):** `create_registro` busca `_role_scoped(ctx).where(client_uuid == data.client_uuid)`; para un ACTIVISTA, `_role_scoped` ya filtra por `activista_id == ctx.user.id`, de modo que el match es **por dueño**. Un re-sync devuelve la misma fila ⇒ sin duplicados. Dos activistas distintos con el mismo `client_uuid` (colisión astronómicamente improbable con UUIDv4) NO se pisan en el lookup (cada uno ve solo el suyo).

---

## 7. Migración: ensanchar el unique constraint

**Problema:** el constraint de SPA-1 es `uq_registros_campaign_client_uuid = UNIQUE(campaign_id, client_uuid)`. La semántica de idempotencia del servicio es **owner-scoped** (por `activista_id`). Hay un desajuste: si dos activistas de la **misma campaña** generaran el mismo `client_uuid`, el lookup owner-scoped no encontraría colisión (devolvería None para el segundo) y el `INSERT` violaría el constraint de BD a nivel campaña → `IntegrityError`. SPA-3 alinea BD ↔ servicio ensanchando a `UNIQUE(campaign_id, activista_id, client_uuid)`.

**Migración 0009** (`backend/alembic/versions/0009_widen_client_uuid_unique.py`):
- `revision = "0009"`, `down_revision = "0008"`.
- **Concern de dos cabezas:** SPA-1 (`0008`) tiene `down_revision = "0006"` deliberadamente porque SP0b-2b (`0007`) está en una rama sin fusionar (`feat/sp0b2b-tidy-facts`). Al fusionar esa rama hará falta una migración de merge (dos `down_revisions`). `0009` cuelga de `0008`; este concern se hereda, no se resuelve aquí — anotarlo en el plan como tarea de integración.
- **Patrones endurecidos** (de 0008 / `prod-recovery-alembic-enums`): helpers `_index_exists` / inspección de constraints; sin `try/except` de control de flujo; idempotente.

**Dialect-safe:**
- **PostgreSQL:** `op.drop_constraint("uq_registros_campaign_client_uuid", "registros", type_="unique")` (guard: solo si existe vía `inspect(bind).get_unique_constraints("registros")`), luego `op.create_unique_constraint("uq_registros_campaign_activista_client_uuid", "registros", ["campaign_id","activista_id","client_uuid"])` (guard: solo si no existe).
- **SQLite (tests):** SQLite no soporta `ALTER TABLE DROP CONSTRAINT`. SPA-1 nunca tuvo que alterar un constraint existente: en `0008` el constraint se definió **inline en `create_table`**, y en los tests la tabla se crea vía `Base.metadata.create_all` (conftest) a partir del **modelo**, no de la migración. Por tanto, para SQLite la fuente de verdad del constraint es el **modelo** (`Registro.__table_args__`), que SPA-3 actualiza al nuevo nombre/columnas. La migración usa `op.batch_alter_table("registros", recreate="auto")` (rebuild de tabla, patrón Alembic estándar en SQLite) o se hace **no-op en SQLite** guardada por `bind.dialect.name == "postgresql"`, dado que los tests parten de un esquema ya correcto desde el modelo. **Decisión recomendada:** rama por dialecto — PG hace drop+create; SQLite usa `batch_alter_table` para que el test offline up/down de la migración (en el plan) también pase contra SQLite.
- **Modelo:** actualizar `Registro.__table_args__` → `UniqueConstraint("campaign_id","activista_id","client_uuid", name="uq_registros_campaign_activista_client_uuid")`. Esto mantiene `create_all` (tests) coherente con la migración (prod).

**Downgrade:** invertir (drop del nuevo, recrear el viejo), simétrico y guardado.

**Verificación:** test offline SQLite `upgrade head → downgrade 0008` sin excepción (patrón del plan SPA-1 Task 4 Step 3); smoke PostGIS opcional.

---

## 8. Privacidad: PII en el dispositivo (riesgo)

La cola IndexedDB almacena el `payload` **en claro**, incluida la **clave de elector** y el teléfono, en el dispositivo del activista hasta que el registro sincroniza y la fila se borra.

- **Superficie:** datos en el propio dispositivo del activista (no en tránsito ni en servidor sin cifrar — el backend cifra con Fernet en reposo, SPA-1). IndexedDB es origin-scoped y no accesible por otros sitios.
- **Mitigaciones aplicadas en SPA-3:** (a) borrar la fila inmediatamente tras `synced` (retención mínima); (b) no loggear PII (Task Pack §4) — `last_error` guarda solo mensajes, nunca el payload; (c) el aviso de privacidad existente en `CapturaPage` ya advierte del tratamiento.
- **Fuera de alcance (decisión a confirmar con el humano):** cifrado-en-reposo en dispositivo del payload encolado (p.ej. WebCrypto AES-GCM con clave derivada). Implica gestión de clave en cliente (¿de dónde sale, dónde vive?) sin un modelo claro de custodia; el beneficio marginal sobre el aislamiento de origen de IndexedDB es bajo para un MVP de campo. Se **anota como riesgo aceptado** y candidato a SPA-4 (compliance). **Pregunta abierta:** ¿se exige cifrado on-device antes de prod?

---

## 9. Concerns de integración

- **Catch-all de la SPA:** verificar que `backend/app/main.py` sirva `/sw.js` y `/manifest.webmanifest` como estáticos (no devolver `index.html`). Si el catch-all los intercepta, el SW no se registra en prod.
- **Caché del SW vs. deploys:** `registerType: "autoUpdate"` + precache versionado de Workbox evita servir un shell viejo; aun así, validar que tras un deploy el cliente recoge la nueva versión (Workbox `skipWaiting`/`clientsClaim` por defecto en `autoUpdate`).
- **Dos cabezas Alembic (0007):** ver §7.
- **Dev vs. prod del SW:** `vite-plugin-pwa` desactiva el SW en `vite dev` salvo `devOptions.enabled`. La verificación offline real se hace contra `npm run build` + `npm run preview`.

---

## 10. Testing

- **No hay runner frontend instalado** (`frontend/package.json` no tiene `vitest`/`jest`). **Decisión recomendada:** añadir **`vitest`** (devDep, integra nativo con Vite) para unit-testear los módulos puros de cola y sync en estilo TDD. Es ligero y no cambia el pipeline de build.
- **Si el humano prefiere no añadir runner:** la puerta mínima es `npm run build` verde **+** los módulos de cola/sync escritos como módulos puros (sin dependencia del SW) verificables manualmente. El diseño ya aísla la lógica para soportar cualquiera de los dos caminos. **Pregunta abierta** (ver cierre).
- **Backend:** `pytest` — test del nuevo constraint (dos activistas, misma campaña, mismo `client_uuid` coexisten; idempotencia por activista intacta) + migración offline up/down. Suite completa verde.
- **Build:** `npm run build` (tsc -b + vite build con plugin PWA) verde; sin `any`.

---

## 11. Resumen de archivos

**Backend — crear:** `backend/alembic/versions/0009_widen_client_uuid_unique.py`.
**Backend — modificar:** `backend/app/models/registro.py` (constraint), `backend/tests/test_registros.py` o `test_registro_permissions.py` (test del constraint).
**Frontend — crear:** `src/offline/db.ts`, `src/offline/queue.ts`, `src/offline/sync.ts`, `src/offline/types.ts`, sus `*.test.ts`; `src/hooks/useOnlineStatus.ts`; `src/store/pendingSyncStore.ts`; `src/components/.../PendingSyncIndicator.tsx`; iconos PWA en `public/`.
**Frontend — modificar:** `vite.config.ts` (VitePWA), `package.json` (`vite-plugin-pwa`, `idb`, opc. `vitest`), `src/modules/captura/CapturaPage.tsx` (client_uuid + submit offline-aware + indicador), opc. `src/main.tsx` (registro SW si no se usa auto).

## 12. Preguntas abiertas

1. **Runner de tests frontend:** ¿añadir `vitest` (recomendado, habilita TDD del módulo de cola) o quedarse con "build verde + módulo puro"?
2. **Cifrado on-device** del payload en IndexedDB: ¿requisito antes de prod o riesgo aceptado para MVP (→ SPA-4)?
3. **Background Sync API** (sync con app cerrada): ¿alcance futuro o suficiente con sync en app abierta?
4. **`vite-plugin-pwa`** como librería PWA (Workbox): ¿confirmado, o se prefiere SW a mano?
</content>
</invoke>
