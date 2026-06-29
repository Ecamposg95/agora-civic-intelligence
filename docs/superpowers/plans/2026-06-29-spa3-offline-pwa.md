# SPA-3 · Captura Offline (PWA + cola IndexedDB + sync) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer la captura de activistas usable en campo sin señal: PWA instalable (app-shell offline), cola IndexedDB de registros, sincronización automática al reconectar con indicador de "pendientes", idempotencia plena por `client_uuid`, y una migración que alinea el unique constraint con la semántica owner-scoped del servicio.

**Architecture:** Construye sobre SPA-1 (rama `feat/spa1-captura-activistas`). Backend: una migración 0009 + ajuste del modelo `Registro`; la lógica de servicio NO cambia (la idempotencia owner-scoped por `client_uuid` ya existe). Frontend: módulos puros y testeables (`src/offline/{db,queue,sync}.ts`) separados del service worker (cascarón Workbox vía `vite-plugin-pwa`), un store de pendientes (Zustand), un hook online/offline, y el cableado de `CapturaPage` para generar/enviar `client_uuid` y encolar cuando no hay red.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Alembic 1.14 (PG/SQLite) · React 18 + TS + Vite 6 + Tailwind + Zustand · **nuevas deps frontend:** `vite-plugin-pwa` (Workbox), `idb`, opc. `vitest`.

## Global Constraints

- **Spec de referencia:** `docs/superpowers/specs/2026-06-29-spa3-offline-pwa-design.md`. Toda tarea hereda sus reglas.
- **Golden Rules (de `docs/architecture.md`):** queries filtran por `organization_id`; `organization_id`/`campaign_id` de escrituras viene del contexto, nunca del body; endpoints devuelven Pydantic; RBAC en API; operaciones sensibles emiten `AuditLog`; sin secretos hardcodeados; listas `{items,total,limit,offset}`; errores `{ "error": { "message", "status" } }`.
- **Sin cambios en la superficie de seguridad:** SPA-3 no expone clave en claro vía API; el cliente sí maneja la clave en claro localmente en la cola IndexedDB (riesgo documentado, spec §8). **No loggear PII** (Task Pack §4): `last_error` guarda solo mensajes, jamás el payload.
- **Idempotencia:** el cliente genera `client_uuid` con `crypto.randomUUID()` al **capturar** (no al enviar) y lo reusa en todos los reintentos. El backend ya deduplica owner-scoped.
- **Migraciones:** patrones endurecidos (guards de existencia de constraint/índice, dialect-safe PG/SQLite, idempotente, sin `try/except` de control de flujo). Head actual: `0008` → nueva: `0009` (`down_revision="0008"`). **Concern de dos cabezas:** SP0b-2b (`0007`) sigue sin fusionar; al fusionarlo hará falta una merge-migration (ver Task 8).
- **Service worker aislado:** toda la lógica de negocio (cola, drenado, máquina de estados) vive en módulos puros TS; el SW es un cascarón generado por Workbox. Esto permite unit tests.
- **Tests:** backend `pytest` verde sin regresiones (SQLite in-memory). Frontend: `npm run build` verde; si se adopta `vitest` (Task 2), los módulos de `src/offline` se desarrollan TDD.
- **Rama:** `feat/spa1-captura-activistas` (SPA-3 continúa sobre ella; no se crea rama nueva salvo decisión del humano).

---

## File Structure

**Backend — crear:**
- `backend/alembic/versions/0009_widen_client_uuid_unique.py` — migración del constraint.

**Backend — modificar:**
- `backend/app/models/registro.py` — `UniqueConstraint` ensanchado a `(campaign_id, activista_id, client_uuid)`.
- `backend/tests/test_registro_permissions.py` (o `test_registros.py`) — test del nuevo constraint + no-regresión de idempotencia.

**Frontend — crear:**
- `frontend/src/offline/types.ts` — tipos de la cola (`QueuedRegistro`, `SyncStatus`).
- `frontend/src/offline/db.ts` — apertura de IndexedDB (`idb`) + acceso al store.
- `frontend/src/offline/queue.ts` — módulo puro: `enqueue/listQueue/markStatus/removeQueued/countPending`.
- `frontend/src/offline/sync.ts` — motor de drenado (máquina de estados) con `createRegistro` inyectado.
- `frontend/src/offline/queue.test.ts`, `frontend/src/offline/sync.test.ts` — unit tests (si `vitest`).
- `frontend/src/hooks/useOnlineStatus.ts` — hook `navigator.onLine` + eventos `online`/`offline`.
- `frontend/src/store/pendingSyncStore.ts` — store Zustand: count pendientes + `triggerSync()` + estado `syncing`.
- `frontend/src/components/captura/PendingSyncIndicator.tsx` — chip "N pendientes" + botón sincronizar.
- `frontend/public/pwa-192.png`, `pwa-512.png`, `pwa-maskable-512.png` — iconos PWA.
- `frontend/vitest.config.ts` (o config dentro de `vite.config.ts`) — si se adopta vitest.

**Frontend — modificar:**
- `frontend/package.json` — deps `vite-plugin-pwa`, `idb` (+ opc. `vitest`, `fake-indexeddb`); scripts `test`.
- `frontend/vite.config.ts` — plugin `VitePWA(...)` (manifest + workbox precache).
- `frontend/src/modules/captura/CapturaPage.tsx` — generar `client_uuid`, submit offline-aware (encolar si no hay red / si el POST falla), montar `PendingSyncIndicator`, sync en arranque.
- `frontend/src/main.tsx` — registro del SW solo si NO se usa `injectRegister: "auto"` (preferir auto → sin cambios).

---

## Task 1 · Migración 0009 — ensanchar unique constraint (BACKEND, parallel-safe)

> **Parallel-safe:** toca solo backend; disjunto de todas las tareas frontend (2–7). Puede ejecutarse en paralelo a ellas.

**Files:**
- Create: `backend/alembic/versions/0009_widen_client_uuid_unique.py`
- Modify: `backend/app/models/registro.py`
- Test: `backend/tests/test_registro_permissions.py`

**Interfaces:**
- Consumes: head `0008` (`down_revision`); modelo `Registro`.
- Produces: constraint `uq_registros_campaign_activista_client_uuid = UNIQUE(campaign_id, activista_id, client_uuid)`; el viejo `uq_registros_campaign_client_uuid` deja de existir.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_registro_permissions.py` (usa el seed SPA-1: `activista1@alpha.gov`, `activista2@alpha.gov`, misma campaña Alpha):
```python
def test_two_activistas_same_campaign_same_client_uuid_coexist(client):
    # Mismo client_uuid, distinta activista, misma campaña → ambos deben crearse.
    h1 = _hdr(client, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
    h2 = _hdr(client, "activista2@alpha.gov", ALPHA_CAMPAIGN_ID)
    p = {"nombre_completo": "Colisión UUID", "consentimiento": True, "client_uuid": "shared-uuid-1"}
    r1 = client.post("/api/registros", json=p, headers=h1)
    r2 = client.post("/api/registros", json=p, headers=h2)
    assert r1.status_code == 201 and r2.status_code == 201, (r1.text, r2.text)
    assert r1.json()["id"] != r2.json()["id"]
    client.delete(f"/api/registros/{r1.json()['id']}", headers=h1)
    client.delete(f"/api/registros/{r2.json()['id']}", headers=h2)


def test_same_activista_same_client_uuid_idempotent(client):
    # No-regresión: el mismo activista reenviando el mismo client_uuid no duplica.
    h = _hdr(client, "activista1@alpha.gov", ALPHA_CAMPAIGN_ID)
    p = {"nombre_completo": "Idem", "consentimiento": True, "client_uuid": "idem-uuid-1"}
    a = client.post("/api/registros", json=p, headers=h)
    b = client.post("/api/registros", json=p, headers=h)
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["id"] == b.json()["id"]
    client.delete(f"/api/registros/{a.json()['id']}", headers=h)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_registro_permissions.py::test_two_activistas_same_campaign_same_client_uuid_coexist -v`
Expected: FAIL — `IntegrityError` por el constraint viejo `(campaign_id, client_uuid)` al insertar la segunda fila. (El segundo lookup owner-scoped no encuentra la fila de la otra activista, intenta INSERT, y el constraint a nivel campaña lo rechaza.)

- [ ] **Step 3: Actualizar el modelo**

En `backend/app/models/registro.py`, reemplazar en `__table_args__`:
```python
        UniqueConstraint("campaign_id", "client_uuid", name="uq_registros_campaign_client_uuid"),
```
por:
```python
        UniqueConstraint(
            "campaign_id", "activista_id", "client_uuid",
            name="uq_registros_campaign_activista_client_uuid",
        ),
```
(Esto hace que `Base.metadata.create_all` en los tests cree la tabla ya con el constraint correcto — fuente de verdad para SQLite.)

- [ ] **Step 4: Escribir la migración**

Crear `backend/alembic/versions/0009_widen_client_uuid_unique.py`, siguiendo los patrones endurecidos de `0008_activistas.py`:
```python
"""SPA-3: widen registros unique constraint to (campaign_id, activista_id, client_uuid).

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-29

Notes
-----
* down_revision is 0008. SP0b-2b (0007) is still on an unmerged branch; when it
  merges, a separate Alembic merge-migration (two down_revisions) is needed.
* Widening a UNIQUE constraint = drop old + create new. PostgreSQL supports
  ALTER TABLE DROP/ADD CONSTRAINT directly. SQLite does not, so it is handled via
  batch_alter_table (table rebuild). Both paths are guarded for idempotency.
* The model (Registro.__table_args__) is the source of truth for SQLite test DBs
  built with create_all; this migration keeps prod PG in sync.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

OLD = "uq_registros_campaign_client_uuid"
NEW = "uq_registros_campaign_activista_client_uuid"
COLS = ["campaign_id", "activista_id", "client_uuid"]


def _uniques(table: str) -> set[str]:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table):
        return set()
    return {uc["name"] for uc in sa.inspect(bind).get_unique_constraints(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("registros"):
        return
    is_pg = bind.dialect.name == "postgresql"
    existing = _uniques("registros")

    if is_pg:
        if OLD in existing:
            op.drop_constraint(OLD, "registros", type_="unique")
        if NEW not in existing:
            op.create_unique_constraint(NEW, "registros", COLS)
    else:
        # SQLite: rebuild the table. Drop old + add new inside one batch op.
        with op.batch_alter_table("registros", schema=None) as batch:
            if OLD in existing:
                batch.drop_constraint(OLD, type_="unique")
            if NEW not in existing:
                batch.create_unique_constraint(NEW, COLS)


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("registros"):
        return
    is_pg = bind.dialect.name == "postgresql"
    existing = _uniques("registros")

    if is_pg:
        if NEW in existing:
            op.drop_constraint(NEW, "registros", type_="unique")
        if OLD not in existing:
            op.create_unique_constraint(OLD, "registros", ["campaign_id", "client_uuid"])
    else:
        with op.batch_alter_table("registros", schema=None) as batch:
            if NEW in existing:
                batch.drop_constraint(NEW, type_="unique")
            if OLD not in existing:
                batch.create_unique_constraint(OLD, ["campaign_id", "client_uuid"])
```

> Nota: confirmar contra `0008` que `get_unique_constraints` reporta el nombre `uq_registros_campaign_client_uuid` en PG (se creó nombrado, así que sí). En SQLite, `batch_alter_table` regenera la tabla con el nuevo constraint nombrado.

- [ ] **Step 5: Verificar migración en SQLite (offline up/down)**

Run:
```bash
cd backend && python -c "
from alembic.config import Config; from alembic import command
import tempfile, os
db = tempfile.mktemp(suffix='.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + db
cfg = Config('alembic.ini')
command.upgrade(cfg, 'head')
command.downgrade(cfg, '0008')
print('migration up/down OK')
"
```
Expected: `migration up/down OK` (sin excepciones).

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/test_registro_permissions.py -v && pytest -q`
Expected: PASS (coexistencia + idempotencia + sin regresiones).

- [ ] **Step 7: Smoke en PostGIS (opcional, recomendado antes de prod)**

Run (como en SP0b-2b): levantar `postgis/postgis:17-3.5`, `alembic upgrade head`, verificar con `\d registros` que existe `uq_registros_campaign_activista_client_uuid` y NO `uq_registros_campaign_client_uuid`.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/registro.py backend/alembic/versions/0009_widen_client_uuid_unique.py backend/tests/test_registro_permissions.py
git commit -m "feat(spa3): widen registros unique constraint to (campaign,activista,client_uuid) — Alembic 0009"
```

---

## Task 2 · Tooling frontend — deps PWA/IndexedDB + runner de tests (FRONTEND, foundation)

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts` (si se adopta vitest)

**Interfaces:**
- Produces: deps `vite-plugin-pwa`, `idb` disponibles; (opc.) `vitest` + `fake-indexeddb` + script `test`.

- [ ] **Step 1: Instalar dependencias**

```bash
cd frontend && npm install idb && npm install -D vite-plugin-pwa
```
(`idb` = wrapper IndexedDB; `vite-plugin-pwa` trae Workbox transitivamente.)

- [ ] **Step 2: (Decisión) Runner de tests**

Si el humano aprueba `vitest` (recomendado — habilita TDD de los módulos puros):
```bash
cd frontend && npm install -D vitest fake-indexeddb
```
Crear `frontend/vitest.config.ts`:
```typescript
import { defineConfig } from "vitest/config";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    environment: "node",
    setupFiles: ["fake-indexeddb/auto"], // polyfill IndexedDB for unit tests
    include: ["src/**/*.test.ts"],
  },
});
```
Y en `frontend/package.json` añadir a `scripts`: `"test": "vitest run"`.

Si el humano NO quiere runner: omitir este step; los módulos de cola/sync se escriben igualmente como puros, y la puerta es `npm run build` verde + revisión manual. **Marcar la decisión en el PR.**

- [ ] **Step 3: Verificar que el build sigue verde**

Run: `cd frontend && npm run build`
Expected: build verde (aún sin usar las nuevas deps).

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts
git commit -m "chore(spa3): add vite-plugin-pwa + idb (+ vitest runner) for offline capture"
```

---

## Task 3 · Cola IndexedDB — tipos + db + módulo puro (FRONTEND, TDD)

**Files:**
- Create: `frontend/src/offline/types.ts`, `frontend/src/offline/db.ts`, `frontend/src/offline/queue.ts`, `frontend/src/offline/queue.test.ts`

**Interfaces:**
- Consumes: `idb`, `RegistroCreate` (de `@/api/registros`).
- Produces:
  - `types.ts`: `type SyncStatus = "queued"|"syncing"|"synced"|"error"`; `interface QueuedRegistro { client_uuid; campaign_id; payload: RegistroCreate; status: SyncStatus; created_at: number; attempts: number; last_error: string|null; server_id: string|null }`.
  - `db.ts`: `getDb(): Promise<IDBPDatabase>` (DB `agora-offline` v1, store `registro_queue` keyPath `client_uuid`, índices `by_status`, `by_created_at`).
  - `queue.ts`: `enqueue(payload, campaign_id): Promise<QueuedRegistro>`, `listQueue(): Promise<QueuedRegistro[]>` (orden `created_at`), `markStatus(uuid, status, patch?): Promise<void>`, `removeQueued(uuid): Promise<void>`, `countPending(): Promise<number>` (cuenta `queued`+`error`).

- [ ] **Step 1: Write the failing test** (`queue.test.ts`)
```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { enqueue, listQueue, markStatus, removeQueued, countPending } from "./queue";
import { getDb } from "./db";

beforeEach(async () => {
  const db = await getDb();
  await db.clear("registro_queue");
});

describe("offline queue", () => {
  it("enqueues with status=queued and a generated client_uuid in the payload", async () => {
    const q = await enqueue({ nombre_completo: "Ana", consentimiento: true }, "camp-1");
    expect(q.status).toBe("queued");
    expect(q.client_uuid).toBeTruthy();
    expect(q.payload.client_uuid).toBe(q.client_uuid); // uuid baked into payload
    expect(q.campaign_id).toBe("camp-1");
  });

  it("counts only pending (queued + error)", async () => {
    const a = await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    const b = await enqueue({ nombre_completo: "B", consentimiento: true }, "c");
    await markStatus(b.client_uuid, "error", { last_error: "net" });
    expect(await countPending()).toBe(2);
    await markStatus(a.client_uuid, "synced");
    expect(await countPending()).toBe(1);
  });

  it("removes a synced row", async () => {
    const a = await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    await removeQueued(a.client_uuid);
    expect(await listQueue()).toHaveLength(0);
  });

  it("re-enqueuing the same client_uuid does not duplicate", async () => {
    const a = await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    // simulate a second enqueue reusing the uuid (idempotent put)
    await markStatus(a.client_uuid, "error");
    expect(await listQueue()).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/offline/queue.test.ts`
Expected: FAIL (módulos inexistentes).
*(Sin vitest: omitir y escribir los módulos directamente; verificar con `npm run build`.)*

- [ ] **Step 3: Implementar `types.ts`, `db.ts`, `queue.ts`**

`db.ts` abre la DB con `idb.openDB("agora-offline", 1, { upgrade(db){ const s = db.createObjectStore("registro_queue",{keyPath:"client_uuid"}); s.createIndex("by_status","status"); s.createIndex("by_created_at","created_at"); } })`.

`queue.ts`:
- `enqueue(payload, campaign_id)`: `const client_uuid = payload.client_uuid ?? crypto.randomUUID();` construye `QueuedRegistro` con `payload: { ...payload, client_uuid }`, `status:"queued"`, `created_at: Date.now()`, `attempts:0`, `last_error:null`, `server_id:null`; `db.put(...)`; retorna el objeto.
- `markStatus(uuid, status, patch?)`: leer, mezclar `{status, ...patch}`, `put`.
- `removeQueued(uuid)`: `db.delete`.
- `listQueue()`: `db.getAllFromIndex("registro_queue","by_created_at")`.
- `countPending()`: contar los de `status in {queued, error}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/offline/queue.test.ts`
Expected: PASS.

- [ ] **Step 5: Build**

Run: `cd frontend && npm run build`
Expected: verde, sin `any`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/offline/types.ts frontend/src/offline/db.ts frontend/src/offline/queue.ts frontend/src/offline/queue.test.ts
git commit -m "feat(spa3): IndexedDB offline queue (pure, unit-tested) for captured registros"
```

---

## Task 4 · Motor de sincronización — máquina de estados (FRONTEND, TDD)

**Files:**
- Create: `frontend/src/offline/sync.ts`, `frontend/src/offline/sync.test.ts`

**Interfaces:**
- Consumes: `queue` (Task 3), un `createRegistro` **inyectado** (de `@/api/registros`), para testabilidad.
- Produces: `drainQueue(deps?: { create?: typeof createRegistro }): Promise<{ synced: number; failed: number }>`. Implementa la máquina `queued/error → syncing → synced(borrar) | error(attempts++)`, con guard `isDraining`, FIFO por `created_at`, y distinción red/5xx (retry) vs 4xx no recuperable (error permanente, no bucle).

- [ ] **Step 1: Write the failing test** (`sync.test.ts`)
```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { enqueue, listQueue, countPending } from "./queue";
import { getDb } from "./db";
import { drainQueue } from "./sync";

beforeEach(async () => { const db = await getDb(); await db.clear("registro_queue"); });

describe("sync engine", () => {
  it("drains queued rows and removes them on success", async () => {
    await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    await enqueue({ nombre_completo: "B", consentimiento: true }, "c");
    const create = async (p: any) => ({ id: "srv-" + p.client_uuid, ...p });
    const res = await drainQueue({ create: create as any });
    expect(res.synced).toBe(2);
    expect(await listQueue()).toHaveLength(0);
  });

  it("keeps row as error on network failure and increments attempts", async () => {
    const q = await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    const create = async () => { throw Object.assign(new Error("Network"), { status: undefined }); };
    const res = await drainQueue({ create: create as any });
    expect(res.failed).toBe(1);
    const rows = await listQueue();
    expect(rows[0].status).toBe("error");
    expect(rows[0].attempts).toBe(1);
    expect(await countPending()).toBe(1); // will retry later
  });

  it("does not duplicate work when called concurrently", async () => {
    await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    let calls = 0;
    const create = async (p: any) => { calls++; return { id: "x", ...p }; };
    await Promise.all([drainQueue({ create: create as any }), drainQueue({ create: create as any })]);
    expect(calls).toBe(1);
  });
});
```

- [ ] **Step 2: Run to verify it fails** → `npx vitest run src/offline/sync.test.ts` (FAIL: `sync.ts` no existe).

- [ ] **Step 3: Implementar `sync.ts`**
- Guard de módulo `let draining = false;` → si `draining`, retornar `{synced:0,failed:0}`.
- `const create = deps?.create ?? createRegistro;`
- Tomar `listQueue()`, filtrar `status in {queued, error}` (orden FIFO ya garantizado).
- Por cada fila: `markStatus(uuid,"syncing")`; `try { await create(row.payload); await removeQueued(uuid); synced++ }` `catch (e) { const status = e?.status; if (status && status >= 400 && status < 500 && status !== 408 && status !== 429) markStatus(uuid,"error",{last_error: msg, attempts: row.attempts+1}) /* permanente */ else markStatus(uuid,"error",{last_error: msg, attempts: row.attempts+1}) /* retry */; failed++ }`. (Ambas ramas marcan `error`; la diferencia es semántica para la UI — opcionalmente un flag `permanent`. Mantener `last_error` sin PII.)
- `finally { draining = false }`.

- [ ] **Step 4: Run to verify it passes** → `npx vitest run src/offline/sync.test.ts` (PASS).

- [ ] **Step 5: Build** → `cd frontend && npm run build` (verde).

- [ ] **Step 6: Commit**
```bash
git add frontend/src/offline/sync.ts frontend/src/offline/sync.test.ts
git commit -m "feat(spa3): offline sync engine (state machine, idempotent drain, injectable API)"
```

---

## Task 5 · Detección online/offline + store de pendientes + indicador (FRONTEND)

**Files:**
- Create: `frontend/src/hooks/useOnlineStatus.ts`, `frontend/src/store/pendingSyncStore.ts`, `frontend/src/components/captura/PendingSyncIndicator.tsx`

**Interfaces:**
- Consumes: `queue.countPending`, `sync.drainQueue`.
- Produces:
  - `useOnlineStatus(): boolean` — refleja `navigator.onLine`, suscrito a `window` `online`/`offline`.
  - `pendingSyncStore` (Zustand): `{ pending: number; syncing: boolean; refresh(): Promise<void>; triggerSync(): Promise<void> }`. `triggerSync` llama `drainQueue` y luego `refresh` (recuenta).
  - `PendingSyncIndicator`: chip "N pendientes por sincronizar" (oculto si 0), spinner cuando `syncing`, botón "Sincronizar ahora" (disabled si offline o syncing), nota "sin conexión" cuando offline.

- [ ] **Step 1: Implementar `useOnlineStatus`** — `useState(navigator.onLine)` + `useEffect` con listeners `online`/`offline`, cleanup correcto.

- [ ] **Step 2: Implementar `pendingSyncStore`** — `create<...>` con `refresh: async () => set({ pending: await countPending() })`, `triggerSync: async () => { set({syncing:true}); try { await drainQueue(); } finally { set({syncing:false}); await get().refresh(); } }`.

- [ ] **Step 3: Implementar `PendingSyncIndicator`** — usa estilos existentes (`metric-chip`, `pill`, `btn-*`), consume el store + `useOnlineStatus`. Sin PII en pantalla (solo conteo).

- [ ] **Step 4: Build** → `cd frontend && npm run build` (verde).

- [ ] **Step 5: Commit**
```bash
git add frontend/src/hooks/useOnlineStatus.ts frontend/src/store/pendingSyncStore.ts frontend/src/components/captura/PendingSyncIndicator.tsx
git commit -m "feat(spa3): online status hook + pending-sync store + indicator"
```

---

## Task 6 · Cablear CapturaPage — client_uuid + submit offline-aware (FRONTEND)

**Files:**
- Modify: `frontend/src/modules/captura/CapturaPage.tsx`

**Interfaces:**
- Consumes: `createRegistro`, `enqueue`, `drainQueue`, `pendingSyncStore`, `useOnlineStatus`, `PendingSyncIndicator`.

- [ ] **Step 1: Generar `client_uuid` por captura**

En `handleSubmit`, construir el payload base (como hoy) y añadir `client_uuid: crypto.randomUUID()`.

- [ ] **Step 2: Submit offline-aware**

Reemplazar el `await createRegistro(...)` directo por:
```text
if (navigator.onLine) {
  try { await createRegistro(payload); }
  catch (e) {
    if (isNetworkError(e)) { await enqueue(payload, campaignId); }  // degradar a cola
    else throw e;                                                    // 4xx real → mostrar error
  }
} else {
  await enqueue(payload, campaignId);
}
```
Tras éxito (online o encolado): limpiar el form, `pendingSyncStore.refresh()`, y si online `void pendingSyncStore.triggerSync()`; recargar `listMisRegistros()`. Mostrar feedback distinto: "Guardado" vs "Guardado sin conexión — se sincronizará". `isNetworkError` = `e.status === undefined` (el interceptor de `client.ts` deja `status` indefinido en fallos de red).

> `campaignId` se obtiene de `localStorage.getItem("agora-campaign")` (ya usado en `CapturaPage` para `hasCampaign`) o del `campaignStore`. Es el snapshot que viaja en la cola.

- [ ] **Step 3: Montar el indicador + sync en arranque**

Renderizar `<PendingSyncIndicator />` (p.ej. junto al chip de "registros" del `PageHeader` o sobre la lista). En un `useEffect` de montaje: `pendingSyncStore.refresh()` y, si `navigator.onLine`, `pendingSyncStore.triggerSync()`. Suscribir al evento `online` (vía `useOnlineStatus` + efecto) para auto-sync al reconectar.

- [ ] **Step 4: Build** → `cd frontend && npm run build` (verde, sin `any`).

- [ ] **Step 5: Verificación manual (preview)**

Run: `cd frontend && npm run build && npm run preview`; en DevTools → Network → Offline: capturar un registro (debe aparecer "pendiente"), volver a Online (debe sincronizar y bajar el contador). Confirmar en backend que NO se duplicó (un solo `client_uuid`).

- [ ] **Step 6: Commit**
```bash
git add frontend/src/modules/captura/CapturaPage.tsx
git commit -m "feat(spa3): CapturaPage sends client_uuid + queues offline + auto-sync on reconnect"
```

---

## Task 7 · PWA — manifest + service worker (Workbox) (FRONTEND, parallel-safe)

> **Parallel-safe:** toca `vite.config.ts`, `public/` y opcionalmente `main.tsx` — disjunto de los módulos `src/offline/*` (Tasks 3–6). Puede hacerse en paralelo a 3–6 tras la Task 2.

**Files:**
- Modify: `frontend/vite.config.ts` (+ opc. `frontend/src/main.tsx`)
- Create: `frontend/public/pwa-192.png`, `pwa-512.png`, `pwa-maskable-512.png`

**Interfaces:**
- Produces: `manifest.webmanifest` + `sw.js` (Workbox) en `dist/`; app-shell precacheado → carga offline.

- [ ] **Step 1: Generar iconos PWA**

Derivar PNG 192/512 + maskable 512 de `frontend/public/favicon.svg` (cualquier herramienta de export). Colocar en `frontend/public/`.

- [ ] **Step 2: Configurar `VitePWA` en `vite.config.ts`**

Añadir a `plugins`:
```typescript
VitePWA({
  registerType: "autoUpdate",
  injectRegister: "auto",
  includeAssets: ["favicon.svg"],
  manifest: {
    name: "Ágora — Captura de Activistas",
    short_name: "Ágora",
    description: "Captura de activistas en campo, también sin conexión.",
    theme_color: "#0b1220",      // alinear al navy del tema
    background_color: "#0b1220",
    display: "standalone",
    start_url: "/",
    icons: [
      { src: "/pwa-192.png", sizes: "192x192", type: "image/png" },
      { src: "/pwa-512.png", sizes: "512x512", type: "image/png" },
      { src: "/pwa-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  },
  workbox: {
    globPatterns: ["**/*.{js,css,html,svg,woff2}"],
    navigateFallback: "/index.html",
    // No cachear /api/* aquí: la ruta offline de captura es la cola IndexedDB.
    navigateFallbackDenylist: [/^\/api\//],
  },
})
```
Importar `import { VitePWA } from "vite-plugin-pwa";`.

- [ ] **Step 3: (Opcional) UX de actualización** — si se quiere aviso "nueva versión", usar `virtual:pwa-register` en `main.tsx`; con `autoUpdate` no es obligatorio.

- [ ] **Step 4: Build + verificar artefactos**

Run: `cd frontend && npm run build`
Expected: `dist/sw.js` y `dist/manifest.webmanifest` generados; build verde.

- [ ] **Step 5: Verificar offline del shell (preview)**

Run: `npm run preview`; en DevTools → Application: SW registrado, manifest válido, app instalable; recargar en modo Offline → el shell carga.

- [ ] **Step 6: Commit**
```bash
git add frontend/vite.config.ts frontend/public/pwa-192.png frontend/public/pwa-512.png frontend/public/pwa-maskable-512.png frontend/src/main.tsx
git commit -m "feat(spa3): installable PWA — manifest + Workbox service worker (app-shell offline)"
```

---

## Task 8 · Integración + verificación end-to-end (BACKEND + FRONTEND)

**Files:**
- Modify (si aplica): `backend/app/main.py` (catch-all que no intercepte `/sw.js` ni `/manifest.webmanifest`).

- [ ] **Step 1: Verificar el catch-all de la SPA**

Inspeccionar `backend/app/main.py`: el catch-all `GET /{path}` → `index.html` NO debe interceptar `/sw.js` ni `/manifest.webmanifest` (deben servirse como estáticos desde `dist/`). Si los intercepta, añadir esos paths al montaje estático / excepción. Verificar con un build servido por el backend.

- [ ] **Step 2: Concern de dos cabezas Alembic (documentar, no resolver)**

Confirmar que `alembic heads` muestra una sola cabeza (`0009`) en esta rama. Anotar en el PR que al fusionar `feat/sp0b2b-tidy-facts` (que aporta `0007`) hará falta una merge-migration que reconcilie `0007` y la cadena `0008→0009` (ver `prod-recovery-alembic-enums` para patrones).

- [ ] **Step 3: Suites verdes**

Run: `cd backend && pytest -q` (verde) · `cd frontend && npm run build` (verde) · si vitest: `npm test` (verde).

- [ ] **Step 4: Smoke offline end-to-end** (preview servido + backend real): capturar offline → reconectar → sincroniza → sin duplicados → `clave_masked` correcta en la lista. Repetir un re-sync forzado (recargar con pendientes ya enviados) para confirmar idempotencia.

- [ ] **Step 5: Commit (si hubo cambios en main.py)**
```bash
git add backend/app/main.py
git commit -m "fix(spa3): serve sw.js + manifest as static (exclude from SPA catch-all)"
```

---

## Self-Review

**Spec coverage:**
- §3 PWA (`vite-plugin-pwa`/Workbox) → Task 2 (dep) + Task 7 ✓
- §4 esquema IndexedDB → Task 3 ✓ · §5 máquina de estados de sync → Task 4 ✓
- §6 idempotencia `client_uuid` (cliente genera+envía) → Task 6 (captura) + Task 3 (baked en payload) ✓; backend ya deduplica (sin cambios) ✓
- §7 migración ensanchando constraint (PG drop+create / SQLite batch) → Task 1 ✓
- §8 privacidad PII en dispositivo → mitigación (borrar tras sync, no loggear PII) en Tasks 3/4; cifrado on-device fuera de alcance (pregunta abierta) ✓
- §9 concerns de integración (catch-all SW, dos cabezas) → Task 8 ✓
- §10 testing (vitest vs build-green) → Task 2 decisión + Tasks 3/4 TDD ✓
- Indicador "pendientes" → Task 5 + Task 6 ✓

**Parallel-safe:** Task 1 (backend, archivos disjuntos) corre en paralelo a todo el frontend. Task 7 (PWA: `vite.config.ts` + `public/` + `main.tsx`) es disjunto de `src/offline/*` y puede correr en paralelo a Tasks 3–6 (tras Task 2). El resto es secuencial por dependencia: Task 2 → {3,4,5} → 6 → 8.

**Type consistency:** `QueuedRegistro`/`SyncStatus` (Task 3 def) usados por `queue`/`sync`/store (Tasks 3–5). `drainQueue(deps)` con `create` inyectable consistente entre Task 4 (def) y Tasks 5/6 (uso). `RegistroCreate.client_uuid?` ya existe en `@/api/registros` (SPA-1) — sin cambios de tipo, solo se rellena. Constraint `uq_registros_campaign_activista_client_uuid` consistente entre modelo (Task 1 Step 3) y migración (Task 1 Step 4).

**Riesgos / decisiones a confirmar:** (1) adoptar `vitest` o no (afecta cómo se ejecutan los TDD steps de Tasks 3/4); (2) cifrado on-device del payload IndexedDB (fuera de alcance propuesto); (3) `vite-plugin-pwa` como elección de librería; (4) generación de iconos PWA (activo a producir). Sin TBD/TODO en el código del plan.
</content>
