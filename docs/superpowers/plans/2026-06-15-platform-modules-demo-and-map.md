# Platform Modules Demo & Map Robustness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Ágora into a demo of the full platform vision — a module framework with active/preview/soon states, 4 flagship modules (Auditoría real; Resultados, Padrón, AI Analyst as labelled previews), 6 coming-soon stubs — and robustify the Map Explorer (interactivity, choropleth, controls, level selector).

**Architecture:** Hybrid by data-reality. Backend stays honest: a real, tenant-scoped `/api/audit` endpoint and a `level` filter on `/api/maps/areas`. Everything else preview-grade is frontend-only with labelled sample fixtures. A central frontend module registry drives both the sidebar and the router so adding a module is one entry.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, pytest (backend); Vite + React 18 + TypeScript + Tailwind, Recharts, MapLibre GL, react-router-dom, Zustand (frontend).

**Reference spec:** `docs/superpowers/specs/2026-06-15-platform-modules-demo-and-map-design.md`

**Conventions in this codebase (follow exactly):**
- Backend run/tests from `backend/`: `cd backend && python3 -m pytest -q`.
- Tenant scoping: `ctx.is_superadmin` → no org filter; else filter by `ctx.organization_id`.
- Pagination envelope: `Page[T]` = `{items, total, limit, offset}`; query params via `PaginationParams` (`limit` 1–200 default 50, `offset` ≥0).
- DB session dep: `DbSession`; tenant dep: `Tenant`; admin gate: `require_roles(UserRole.ADMIN)`.
- Frontend build/typecheck: `cd frontend && npm run build` (runs `tsc -b` then vite).
- Frontend API calls go through `apiClient` (`src/api/client.ts`), token auto-attached.
- Dark theme primitives: `Card`, `MetricCard`, `panel`/`pill` classes, icons in `src/components/ui/icons.tsx`.

---

## File Structure

**Backend (created/modified):**
- Modify `backend/app/services/map_service.py` — add optional `level` to `list_areas_geojson`.
- Modify `backend/app/routers/maps.py` — accept `level` query param.
- Create `backend/app/schemas/audit.py` — `AuditEntry` response schema.
- Modify `backend/app/services/audit_service.py` — add `list_events(...)`.
- Create `backend/app/routers/audit.py` — `GET /api/audit`.
- Modify `backend/app/main.py` — register the audit router.
- Create `backend/tests/test_maps.py` — areas + level filter.
- Create `backend/tests/test_audit.py` — auth, scoping, pagination, filter.

**Frontend framework (created/modified):**
- Create `frontend/src/modules/registry.ts` — `ModuleDef` + `MODULES`.
- Create `frontend/src/components/ui/ModuleBadge.tsx`.
- Create `frontend/src/components/modules/PreviewBanner.tsx`.
- Create `frontend/src/components/modules/ComingSoonPage.tsx`.
- Modify `frontend/src/components/layout/Sidebar.tsx` — render from registry.
- Modify `frontend/src/App.tsx` — build routes from registry.

**Frontend flagship modules:**
- Create `frontend/src/types/audit.ts`, `frontend/src/api/audit.ts`, `frontend/src/modules/auditoria/AuditoriaPage.tsx`.
- Create `frontend/src/modules/resultados/{fixtures.ts,ResultadosPage.tsx}`.
- Create `frontend/src/modules/padron/{fixtures.ts,PadronPage.tsx}`.
- Create `frontend/src/modules/ai-analyst/{client.ts,fixtures.ts,AiAnalystPage.tsx}`.

**Map robustness:**
- Modify `frontend/src/api/maps.ts` — `getAreas(level?)`.
- Modify `frontend/src/components/maps/MapCanvas.tsx` — choropleth, click/hover, basemap, fit-bounds.
- Create `frontend/src/components/maps/{Legend.tsx,AreaDetailPanel.tsx,MapToolbar.tsx}`.
- Modify `frontend/src/pages/MapExplorerPage.tsx` — wire new controls/state.

---

# Phase W1 — Module framework & coming-soon stubs

Independently shippable: introduces the registry, badges, banner, coming-soon template, refactors sidebar + routes to be registry-driven, and adds 6 stub modules.

### Task 1: Module registry types and data

**Files:**
- Create: `frontend/src/modules/registry.ts`

- [ ] **Step 1: Create the registry**

```ts
import { lazy, type ComponentType, type LazyExoticComponent } from "react";

import {
  AiIcon,
  AlertIcon,
  AnalyticsIcon,
  DashboardIcon,
  DatabaseIcon,
  LayersIcon,
  MapIcon,
  SettingsIcon,
  ShieldIcon,
  UserIcon,
  VotersIcon,
} from "@/components/ui/icons";

export type ModuleState = "active" | "preview" | "soon";
export type ModuleSection =
  | "plataforma"
  | "inteligencia"
  | "ciudadania"
  | "gobernanza"
  | "administracion";

export interface SoonCopy {
  summary: string;
  features: string[];
  dataSource: string;
}

export interface ModuleDef {
  key: string;
  path: string;
  label: string;
  section: ModuleSection;
  icon: ComponentType<{ width?: number; height?: number; className?: string }>;
  state: ModuleState;
  /** Restrict to roles; omit = any authenticated user. */
  roles?: ("superadmin" | "admin" | "analyst" | "viewer")[];
  /** Component for active/preview modules. soon → ComingSoonPage. */
  element?: LazyExoticComponent<ComponentType>;
  /** End-match for the index route. */
  end?: boolean;
  soon?: SoonCopy;
}

export const SECTION_LABELS: Record<ModuleSection, string> = {
  plataforma: "Plataforma",
  inteligencia: "Inteligencia Electoral",
  ciudadania: "Ciudadanía",
  gobernanza: "Gobernanza",
  administracion: "Administración",
};

export const SECTION_ORDER: ModuleSection[] = [
  "plataforma",
  "inteligencia",
  "ciudadania",
  "gobernanza",
  "administracion",
];

const Dashboard = lazy(() =>
  import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const MapExplorer = lazy(() =>
  import("@/pages/MapExplorerPage").then((m) => ({ default: m.MapExplorerPage })),
);
const Analytics = lazy(() =>
  import("@/pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })),
);
const Sources = lazy(() =>
  import("@/pages/SourcesPage").then((m) => ({ default: m.SourcesPage })),
);
const Users = lazy(() =>
  import("@/pages/UsersPage").then((m) => ({ default: m.UsersPage })),
);
const Organization = lazy(() =>
  import("@/pages/OrganizationSettingsPage").then((m) => ({
    default: m.OrganizationSettingsPage,
  })),
);
const Resultados = lazy(() =>
  import("@/modules/resultados/ResultadosPage").then((m) => ({
    default: m.ResultadosPage,
  })),
);
const Padron = lazy(() =>
  import("@/modules/padron/PadronPage").then((m) => ({ default: m.PadronPage })),
);
const AiAnalyst = lazy(() =>
  import("@/modules/ai-analyst/AiAnalystPage").then((m) => ({
    default: m.AiAnalystPage,
  })),
);
const Auditoria = lazy(() =>
  import("@/modules/auditoria/AuditoriaPage").then((m) => ({
    default: m.AuditoriaPage,
  })),
);

export const MODULES: ModuleDef[] = [
  // Plataforma (active)
  { key: "dashboard", path: "/", label: "Command Center", section: "plataforma", icon: DashboardIcon, state: "active", element: Dashboard, end: true },
  { key: "maps", path: "/maps", label: "Map Explorer", section: "plataforma", icon: MapIcon, state: "active", element: MapExplorer },
  { key: "analytics", path: "/analytics", label: "Activity Analytics", section: "plataforma", icon: AnalyticsIcon, state: "active", element: Analytics },
  { key: "sources", path: "/sources", label: "Fuentes de datos", section: "plataforma", icon: DatabaseIcon, state: "active", element: Sources },

  // Inteligencia Electoral
  { key: "resultados", path: "/resultados", label: "Resultados Electorales", section: "inteligencia", icon: AnalyticsIcon, state: "preview", element: Resultados },
  { key: "padron", path: "/padron", label: "Padrón / Lista Nominal", section: "inteligencia", icon: VotersIcon, state: "preview", element: Padron },
  {
    key: "candidaturas", path: "/candidaturas", label: "Candidaturas", section: "inteligencia", icon: UserIcon, state: "soon",
    soon: {
      summary: "Registro y seguimiento de candidaturas por cargo, partido y territorio.",
      features: ["Directorio de candidaturas por elección", "Filtros por partido, cargo y entidad", "Fichas con trayectoria y vínculos"],
      dataSource: "Candidaturas MX (apielectoral.mx) — ya integrada en el backend.",
    },
  },
  {
    key: "territorios", path: "/territorios", label: "Territorios & Secciones", section: "inteligencia", icon: LayersIcon, state: "soon",
    soon: {
      summary: "Drill-down geográfico: entidad → distrito → sección → casilla.",
      features: ["Jerarquía territorial navegable", "Métricas por nivel", "Exportación de cortes territoriales"],
      dataSource: "Marco Geográfico Electoral (SIGE/INE) vía ingest de cartografía.",
    },
  },

  // Ciudadanía
  { key: "ai-analyst", path: "/ai-analyst", label: "AI Analyst / Copiloto", section: "ciudadania", icon: AiIcon, state: "preview", element: AiAnalyst },
  {
    key: "sentimiento", path: "/sentimiento", label: "Sentimiento Ciudadano", section: "ciudadania", icon: AnalyticsIcon, state: "soon",
    soon: {
      summary: "Escucha social y de medios sobre temas y actores cívicos.",
      features: ["Tendencias de conversación", "Análisis de sentimiento por tema", "Alertas de picos de actividad"],
      dataSource: "APIs de redes/medios (pendiente de contratar).",
    },
  },
  {
    key: "participacion", path: "/participacion", label: "Participación Ciudadana", section: "ciudadania", icon: VotersIcon, state: "soon",
    soon: {
      summary: "Consultas, peticiones y encuestas ciudadanas gobernadas.",
      features: ["Consultas y peticiones", "Encuestas con resultados auditables", "Tablero de participación"],
      dataSource: "Módulo propio de captación (por construir).",
    },
  },
  {
    key: "riesgo", path: "/riesgo", label: "Alertas & Riesgo Electoral", section: "ciudadania", icon: AlertIcon, state: "soon",
    soon: {
      summary: "Detección de anomalías y monitoreo de riesgo en territorio.",
      features: ["Anomalías estadísticas en resultados", "Mapa de zonas de riesgo", "Alertas configurables"],
      dataSource: "Modelos sobre PREP/cómputos + señales territoriales.",
    },
  },

  // Gobernanza
  { key: "auditoria", path: "/auditoria", label: "Auditoría & Cumplimiento", section: "gobernanza", icon: ShieldIcon, state: "active", element: Auditoria, roles: ["superadmin", "admin"] },
  {
    key: "reportes", path: "/reportes", label: "Reportes Ejecutivos", section: "gobernanza", icon: DatabaseIcon, state: "soon",
    soon: {
      summary: "Briefings ejecutivos generados y exportables (PDF/CSV).",
      features: ["Plantillas de briefing", "Exportación programada", "Distribución por rol"],
      dataSource: "Composición sobre módulos activos de la plataforma.",
    },
  },

  // Administración (role-gated, active)
  { key: "users", path: "/users", label: "Usuarios", section: "administracion", icon: UserIcon, state: "active", element: Users, roles: ["superadmin", "admin"] },
  { key: "organization", path: "/organization", label: "Organización", section: "administracion", icon: SettingsIcon, state: "active", element: Organization, roles: ["superadmin", "admin"] },
];
```

- [ ] **Step 2: Verify icons referenced exist**

Run: `cd frontend && grep -oE "export const [A-Za-z]+Icon" src/components/ui/icons.tsx | sort`
Expected: includes `AiIcon, AlertIcon, AnalyticsIcon, DashboardIcon, DatabaseIcon, LayersIcon, MapIcon, SettingsIcon, ShieldIcon, UserIcon, VotersIcon`. If any is missing, add a minimal SVG icon export to `icons.tsx` mirroring an existing one before continuing.

- [ ] **Step 3: Commit** (registry won't typecheck until the lazy pages exist; that's fine — it's committed with later tasks. Skip commit here and commit at Task 7.)

---

### Task 2: ModuleBadge component

**Files:**
- Create: `frontend/src/components/ui/ModuleBadge.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { ModuleState } from "@/modules/registry";

const STYLES: Record<ModuleState, { label: string; cls: string } | null> = {
  active: null,
  preview: { label: "Preview", cls: "border-state-warning/30 bg-state-warning/10 text-state-warning" },
  soon: { label: "Pronto", cls: "border-teal/30 bg-teal/10 text-teal" },
};

export function ModuleBadge({ state }: { state: ModuleState }) {
  const s = STYLES[state];
  if (!s) return null;
  return <span className={`pill ${s.cls}`}>{s.label}</span>;
}
```

- [ ] **Step 2: Commit at Task 7.**

---

### Task 3: PreviewBanner component

**Files:**
- Create: `frontend/src/components/modules/PreviewBanner.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { AlertIcon } from "@/components/ui/icons";

export function PreviewBanner({ note }: { note?: string }) {
  return (
    <div className="mb-5 flex items-center gap-2.5 rounded-lg border border-state-warning/30 bg-state-warning/10 px-3 py-2.5 text-sm text-state-warning">
      <AlertIcon width={16} height={16} className="shrink-0" />
      <span>
        {note ?? "Datos de muestra · Preview de la plataforma. Las cifras son ilustrativas."}
      </span>
    </div>
  );
}
```

- [ ] **Step 2: Commit at Task 7.**

---

### Task 4: ComingSoonPage component

**Files:**
- Create: `frontend/src/components/modules/ComingSoonPage.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { AppLayout } from "@/components/layout/AppLayout";
import { Card } from "@/components/ui/Card";
import type { ModuleDef } from "@/modules/registry";

export function ComingSoonPage({ module }: { module: ModuleDef }) {
  const Icon = module.icon;
  const soon = module.soon;
  return (
    <AppLayout title={module.label} crumb="Próximamente">
      <div className="mb-6 flex items-start gap-4">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-accent/15 text-accent">
          <Icon width={24} height={24} />
        </div>
        <div>
          <div className="eyebrow">Módulo en desarrollo</div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
            {module.label}
            <span className="ml-3 pill border-teal/30 bg-teal/10 text-teal align-middle">Pronto</span>
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-ink-muted">{soon?.summary}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Capacidades previstas">
          <ul className="space-y-2">
            {soon?.features.map((f) => (
              <li key={f} className="flex items-start gap-2.5 rounded-lg border border-line bg-bg-sunken px-3 py-2.5 text-sm text-ink">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                {f}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Fuente de datos prevista">
          <p className="text-sm leading-relaxed text-ink-muted">{soon?.dataSource}</p>
        </Card>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 2: Commit at Task 7.**

---

### Task 5: Refactor Sidebar to render from the registry

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx` (full replace)

- [ ] **Step 1: Replace the file**

```tsx
import { NavLink } from "react-router-dom";

import { ModuleBadge } from "@/components/ui/ModuleBadge";
import { LogoMark } from "@/components/ui/icons";
import {
  MODULES,
  SECTION_LABELS,
  SECTION_ORDER,
  type ModuleDef,
} from "@/modules/registry";
import { useAuthStore } from "@/store/authStore";

const navItem =
  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors";
const sectionLabel =
  "mt-7 mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-faint";

function visibleFor(role: string | undefined, m: ModuleDef): boolean {
  if (!m.roles) return true;
  return !!role && m.roles.includes(role as never);
}

export function Sidebar() {
  const role = useAuthStore((s) => s.user?.role);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `${navItem} ${
      isActive ? "bg-accent/10 text-accent" : "text-ink-muted hover:bg-panel-hover hover:text-ink"
    }`;

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-line bg-panel px-4 py-5">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-accent/15 text-accent">
          <LogoMark width={20} height={20} />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight text-ink">Ágora</div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-ink-faint">
            Civic Intelligence
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {SECTION_ORDER.map((section) => {
          const items = MODULES.filter(
            (m) => m.section === section && visibleFor(role, m),
          );
          if (items.length === 0) return null;
          return (
            <div key={section}>
              <div className={sectionLabel}>{SECTION_LABELS[section]}</div>
              <nav className="flex flex-col gap-1">
                {items.map((m) => {
                  const Icon = m.icon;
                  return (
                    <NavLink key={m.key} to={m.path} end={m.end} className={linkClass}>
                      <Icon width={18} height={18} />
                      <span className="flex-1">{m.label}</span>
                      <ModuleBadge state={m.state} />
                    </NavLink>
                  );
                })}
              </nav>
            </div>
          );
        })}
      </div>

      <div className="px-3 pt-6 text-[11px] leading-relaxed text-ink-faint">
        Atlas Tech · GovTech
        <br />
        <span className="opacity-70">v0.2.0 · Platform demo</span>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Commit at Task 7.**

---

### Task 6: Refactor App routes to build from the registry

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Read the current file**

Run: `sed -n '1,140p' frontend/src/App.tsx` — note the existing `RequireAuth`, `RouteFallback`, `BrowserRouter/Suspense/Routes` structure and the `/login` + `/change-password` routes. Keep those.

- [ ] **Step 2: Replace the authenticated route block**

Remove the per-page `<Route path="/maps" …>` … `<Route path="/organization" …>` entries and replace the inside of `<Routes>` (after the `/login` and `/change-password` routes) with registry-generated routes:

```tsx
import { ComingSoonPage } from "@/components/modules/ComingSoonPage";
import { MODULES } from "@/modules/registry";
// ...keep existing imports for BrowserRouter, RequireAuth, Suspense, RouteFallback, LoginPage, ChangePasswordPage...

// inside <Routes>, after the /login and /change-password routes:
{MODULES.map((m) => {
  const Element = m.element;
  const node =
    m.state === "soon" || !Element ? <ComingSoonPage module={m} /> : <Element />;
  return (
    <Route
      key={m.key}
      path={m.path}
      element={<RequireAuth>{node}</RequireAuth>}
    />
  );
})}
<Route path="*" element={<Navigate to="/" replace />} />
```

Notes:
- `RequireAuth` already redirects unauthenticated users to `/login` and users with `must_change_password` to `/change-password` — keep it wrapping every module route.
- Role gating in the registry controls the **sidebar**; routes remain reachable by URL but the pages themselves already enforce permissions via the API (admin endpoints 403). This matches current behavior.
- Remove now-unused direct page imports that the registry now lazy-loads (e.g. `DashboardPage`, `MapExplorerPage`, etc.) to avoid `tsc` unused-import errors. Keep `LoginPage`, `ChangePasswordPage`, `Navigate`.

- [ ] **Step 3: Commit at Task 7.**

---

### Task 7: Build and commit the framework

- [ ] **Step 1: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: PASS (the registry lazy-imports `@/modules/resultados/ResultadosPage` etc. — these don't exist yet, so the build WILL fail here). To make W1 self-contained, temporarily create empty stub pages so the build passes, then replace them in W2.

- [ ] **Step 2: Create temporary stub pages so W1 builds**

Create these four files, each exporting a named component that renders `<ComingSoonPage>`-like placeholder. Minimal content:

```tsx
// frontend/src/modules/resultados/ResultadosPage.tsx
import { AppLayout } from "@/components/layout/AppLayout";
export function ResultadosPage() {
  return <AppLayout title="Resultados Electorales" crumb="Preview">Preview en construcción.</AppLayout>;
}
```

Repeat for:
- `frontend/src/modules/padron/PadronPage.tsx` → `PadronPage`
- `frontend/src/modules/ai-analyst/AiAnalystPage.tsx` → `AiAnalystPage`
- `frontend/src/modules/auditoria/AuditoriaPage.tsx` → `AuditoriaPage`

- [ ] **Step 3: Build again**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /mnt/c/Users/ecamp/Devs/agora-civic-intelligence
git add frontend/src/modules frontend/src/components/ui/ModuleBadge.tsx \
  frontend/src/components/modules frontend/src/components/layout/Sidebar.tsx frontend/src/App.tsx
git commit -m "feat(modules): registry-driven nav/routes + module states (W1)"
```

---

# Phase W2 — Flagship modules

## Auditoría & Cumplimiento (REAL)

### Task 8: Audit response schema

**Files:**
- Create: `backend/app/schemas/audit.py`

- [ ] **Step 1: Create the schema**

```python
"""Audit log read schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditEntry(BaseModel):
    """A single audit-trail entry (read model)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    actor_id: Optional[str] = None
    organization_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    created_at: datetime
```

- [ ] **Step 2: Commit at Task 12.**

---

### Task 9: `list_events` service (TDD)

**Files:**
- Modify: `backend/app/services/audit_service.py`
- Test: `backend/tests/test_audit.py` (created in Task 11; service tested via the API there)

- [ ] **Step 1: Add the query function**

Append to `backend/app/services/audit_service.py`:

```python
from datetime import datetime  # add to imports

from sqlalchemy import desc, func, select  # add to imports

from app.dependencies import TenantContext  # add to imports


def list_events(
    db: Session,
    ctx: TenantContext,
    *,
    action: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """Return (items, total) of audit entries, tenant-scoped and newest-first."""
    filters = []
    if not ctx.is_superadmin:
        filters.append(AuditLog.organization_id == ctx.organization_id)
    if action:
        filters.append(AuditLog.action == action)
    if since is not None:
        filters.append(AuditLog.created_at >= since)

    base = select(AuditLog).where(*filters) if filters else select(AuditLog)
    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    items = (
        db.execute(
            base.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return list(items), int(total)
```

- [ ] **Step 2: Commit at Task 12.**

---

### Task 10: Audit router

**Files:**
- Create: `backend/app/routers/audit.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

```python
"""Audit router — read-only access to the tenant-scoped audit trail."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import DbSession, TenantContext, require_roles
from app.models.user import UserRole
from app.schemas.audit import AuditEntry
from app.schemas.pagination import Page
from app.services import audit_service
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/audit", tags=["audit"])

AuditCtx = Annotated[TenantContext, Depends(require_roles(UserRole.ADMIN))]


@router.get("", summary="List audit entries", response_model=Page[AuditEntry])
def list_audit(
    ctx: AuditCtx,
    db: DbSession,
    pagination: Annotated[PaginationParams, Depends()],
    action: Optional[str] = Query(None, description="Filter by exact action"),
    since: Optional[datetime] = Query(None, description="Only entries at/after this UTC time"),
) -> Page[AuditEntry]:
    items, total = audit_service.list_events(
        db, ctx, action=action, since=since,
        limit=pagination.limit, offset=pagination.offset,
    )
    return Page[AuditEntry](
        items=[AuditEntry.model_validate(i) for i in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
```

- [ ] **Step 2: Register the router in `backend/app/main.py`**

In the import block add `audit`:

```python
from app.routers import (
    analytics,
    audit,
    auth,
    health,
    maps,
    organizations,
    sources,
    users,
)
```

In `_register_routers`, add `audit` to the tuple:

```python
    for module in (health, auth, users, organizations, maps, analytics, sources, audit):
        app.include_router(module.router, prefix=prefix)
```

- [ ] **Step 3: Commit at Task 12.**

---

### Task 11: Audit tests (TDD — write, run red, then they pass with Tasks 8–10)

**Files:**
- Create: `backend/tests/test_audit.py`

- [ ] **Step 1: Write the tests**

```python
"""Tests for the read-only audit endpoint."""

from .conftest import auth_headers


def _seed_login_events(client):
    # Each successful login writes an audit entry (auth flow records it).
    auth_headers(client, "admin@alpha.gov")
    auth_headers(client, "admin@alpha.gov")


def test_audit_requires_auth(client):
    assert client.get("/api/audit").status_code == 401


def test_viewer_forbidden(client):
    headers = auth_headers(client, "viewer@alpha.gov")
    assert client.get("/api/audit", headers=headers).status_code == 403


def test_admin_sees_paginated_tenant_events(client):
    _seed_login_events(client)
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/audit?limit=5", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) >= {"items", "total", "limit", "offset"}
    assert body["limit"] == 5
    assert body["total"] >= 1
    for item in body["items"]:
        assert {"id", "action", "created_at"} <= set(item)


def test_action_filter(client):
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/audit?action=auth.login", headers=headers)
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        assert item["action"] == "auth.login"
```

- [ ] **Step 2: Confirm the real audit action string**

Run: `cd backend && grep -rn "record_audit(" app/ | grep -i login`
Expected: find the action string used on login (e.g. `"auth.login"`). If it differs, update `test_action_filter` to that exact string.

- [ ] **Step 3: Run tests RED (before Tasks 8–10 wired)**

Run: `cd backend && python3 -m pytest tests/test_audit.py -q`
Expected: FAIL (404 / no route) until Tasks 8–10 are in place.

- [ ] **Step 4: Run tests GREEN (after Tasks 8–10)**

Run: `cd backend && python3 -m pytest -q`
Expected: PASS (all tests, including prior 27).

- [ ] **Step 5: Commit at Task 12.**

---

### Task 12: Auditoría frontend (real)

**Files:**
- Create: `frontend/src/types/audit.ts`, `frontend/src/api/audit.ts`
- Replace: `frontend/src/modules/auditoria/AuditoriaPage.tsx`

- [ ] **Step 1: Types**

```ts
// frontend/src/types/audit.ts
export interface AuditEntry {
  id: string;
  action: string;
  actor_id: string | null;
  organization_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}
```

- [ ] **Step 2: API**

```ts
// frontend/src/api/audit.ts
import { apiClient } from "./client";
import type { AuditPage } from "@/types/audit";

export async function getAudit(params: {
  limit?: number;
  offset?: number;
  action?: string;
} = {}): Promise<AuditPage> {
  const { data } = await apiClient.get<AuditPage>("/audit", { params });
  return data;
}
```

- [ ] **Step 3: Page (replace the stub)**

```tsx
// frontend/src/modules/auditoria/AuditoriaPage.tsx
import { useEffect, useState } from "react";

import { getAudit } from "@/api/audit";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { ShieldIcon } from "@/components/ui/icons";
import type { AuditPage } from "@/types/audit";

const PAGE = 20;

export function AuditoriaPage() {
  const [data, setData] = useState<AuditPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAudit({ limit: PAGE, offset, action: action || undefined })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [offset, action]);

  const items = data?.items ?? [];

  return (
    <AppLayout title="Auditoría & Cumplimiento" crumb="Gobernanza">
      <div className="mb-6">
        <div className="eyebrow">Gobernanza de datos</div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Auditoría & Cumplimiento
        </h1>
        <p className="mt-1 max-w-xl text-sm text-ink-muted">
          Bitácora inmutable de acciones sensibles, con alcance por organización.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
          {error}
        </div>
      )}

      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard label="Eventos totales" value={data ? String(data.total) : "—"} icon={<ShieldIcon width={18} height={18} />} />
        <MetricCard label="Trazabilidad" value="Inmutable" />
        <MetricCard label="Alcance" value="Tenant-scoped" />
      </div>

      <Card
        title="Bitácora"
        action={
          <input
            value={action}
            onChange={(e) => { setOffset(0); setAction(e.target.value); }}
            placeholder="Filtrar por acción…"
            className="rounded-lg border border-line bg-bg-sunken px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint"
          />
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-ink-faint">
                <th className="px-2 py-2">Fecha</th>
                <th className="px-2 py-2">Acción</th>
                <th className="px-2 py-2">Entidad</th>
                <th className="px-2 py-2">Actor</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} className="border-t border-line">
                  <td className="px-2 py-2 text-ink-muted">{new Date(e.created_at).toLocaleString()}</td>
                  <td className="px-2 py-2"><span className="pill border-accent/30 bg-accent/10 text-accent">{e.action}</span></td>
                  <td className="px-2 py-2 text-ink-muted">{e.entity_type ?? "—"}</td>
                  <td className="px-2 py-2 text-ink-faint">{e.actor_id ? e.actor_id.slice(0, 8) : "system"}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td colSpan={4} className="px-2 py-6 text-center text-ink-faint">Sin eventos.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex items-center justify-between text-sm text-ink-muted">
          <span>{data ? `${offset + 1}–${Math.min(offset + PAGE, data.total)} de ${data.total}` : ""}</span>
          <div className="flex gap-2">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} className="pill border-line disabled:opacity-40">Anterior</button>
            <button disabled={!data || offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)} className="pill border-line disabled:opacity-40">Siguiente</button>
          </div>
        </div>
      </Card>
    </AppLayout>
  );
}
```

- [ ] **Step 4: Build + run backend tests + commit**

Run: `cd frontend && npm run build` → PASS
Run: `cd backend && python3 -m pytest -q` → PASS

```bash
cd /mnt/c/Users/ecamp/Devs/agora-civic-intelligence
git add backend/app/schemas/audit.py backend/app/services/audit_service.py \
  backend/app/routers/audit.py backend/app/main.py backend/tests/test_audit.py \
  frontend/src/types/audit.ts frontend/src/api/audit.ts frontend/src/modules/auditoria/AuditoriaPage.tsx
git commit -m "feat(audit): real tenant-scoped /api/audit endpoint + Auditoría module (W2)"
```

---

### Task 13: Resultados Electorales (preview)

**Files:**
- Create: `frontend/src/modules/resultados/fixtures.ts`
- Replace: `frontend/src/modules/resultados/ResultadosPage.tsx`

- [ ] **Step 1: Fixtures**

```ts
// frontend/src/modules/resultados/fixtures.ts
export interface PartyResult { party: string; color: string; votes: number; share: number; }
export interface EntityResult { entity: string; turnout: number; winner: string; margin: number; }

export const NATIONAL = { turnout: 0.612, counted: 0.973, leader: "Coalición A" };

export const PARTY_RESULTS: PartyResult[] = [
  { party: "Coalición A", color: "#4f9cff", votes: 18432110, share: 0.41 },
  { party: "Coalición B", color: "#f59e0b", votes: 14211980, share: 0.316 },
  { party: "Coalición C", color: "#2dd4bf", votes: 8123450, share: 0.181 },
  { party: "Otros", color: "#7c8aa5", votes: 4187220, share: 0.093 },
];

export const ENTITY_RESULTS: EntityResult[] = [
  { entity: "Ciudad de México", turnout: 0.66, winner: "Coalición A", margin: 0.12 },
  { entity: "Jalisco", turnout: 0.59, winner: "Coalición B", margin: 0.05 },
  { entity: "Nuevo León", turnout: 0.63, winner: "Coalición A", margin: 0.08 },
  { entity: "Veracruz", turnout: 0.57, winner: "Coalición C", margin: 0.03 },
  { entity: "Estado de México", turnout: 0.61, winner: "Coalición A", margin: 0.09 },
];
```

- [ ] **Step 2: Page**

```tsx
// frontend/src/modules/resultados/ResultadosPage.tsx
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppLayout } from "@/components/layout/AppLayout";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { ENTITY_RESULTS, NATIONAL, PARTY_RESULTS } from "./fixtures";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export function ResultadosPage() {
  return (
    <AppLayout title="Resultados Electorales" crumb="Inteligencia Electoral">
      <PreviewBanner />
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard label="Participación nacional" value={pct(NATIONAL.turnout)} />
        <MetricCard label="Casillas computadas" value={pct(NATIONAL.counted)} />
        <MetricCard label="Fuerza líder" value={NATIONAL.leader} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Distribución del voto">
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={PARTY_RESULTS} layout="vertical" margin={{ left: 24 }}>
                <XAxis type="number" tickFormatter={pct} stroke="#5e6f8f" tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="party" stroke="#5e6f8f" tick={{ fontSize: 12 }} width={110} />
                <Tooltip formatter={(v: number) => pct(v)} contentStyle={{ background: "#0d1422", border: "1px solid #2a3a5c", borderRadius: 10 }} />
                <Bar dataKey="share" radius={[0, 6, 6, 0]}>
                  {PARTY_RESULTS.map((p) => <Cell key={p.party} fill={p.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Resultados por entidad">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wide text-ink-faint">
                <th className="px-2 py-2">Entidad</th><th className="px-2 py-2">Participación</th><th className="px-2 py-2">Ganador</th><th className="px-2 py-2">Margen</th>
              </tr></thead>
              <tbody>
                {ENTITY_RESULTS.map((e) => (
                  <tr key={e.entity} className="border-t border-line">
                    <td className="px-2 py-2 text-ink">{e.entity}</td>
                    <td className="px-2 py-2 text-ink-muted">{pct(e.turnout)}</td>
                    <td className="px-2 py-2"><span className="pill border-accent/30 bg-accent/10 text-accent">{e.winner}</span></td>
                    <td className="px-2 py-2 text-ink-muted">{pct(e.margin)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 3: Build + commit**

Run: `cd frontend && npm run build` → PASS

```bash
git add frontend/src/modules/resultados
git commit -m "feat(resultados): Resultados Electorales preview module (W2)"
```

---

### Task 14: Padrón / Lista Nominal (preview)

**Files:**
- Create: `frontend/src/modules/padron/fixtures.ts`
- Replace: `frontend/src/modules/padron/PadronPage.tsx`

- [ ] **Step 1: Fixtures**

```ts
// frontend/src/modules/padron/fixtures.ts
export interface AgeBand { band: string; hombres: number; mujeres: number; }
export interface EntityPadron { entity: string; padron: number; }

export const SUMMARY = { padron: 98_500_000, listaNominal: 97_800_000, cobertura: 0.964, edadMediana: 39 };

export const AGE_BANDS: AgeBand[] = [
  { band: "18–24", hombres: 6.1, mujeres: 6.0 },
  { band: "25–34", hombres: 9.4, mujeres: 9.7 },
  { band: "35–44", hombres: 8.2, mujeres: 8.6 },
  { band: "45–54", hombres: 6.7, mujeres: 7.1 },
  { band: "55–64", hombres: 4.9, mujeres: 5.3 },
  { band: "65+", hombres: 4.1, mujeres: 5.0 },
];

export const TOP_ENTITIES: EntityPadron[] = [
  { entity: "Estado de México", padron: 12_900_000 },
  { entity: "Ciudad de México", padron: 7_700_000 },
  { entity: "Jalisco", padron: 6_300_000 },
  { entity: "Veracruz", padron: 5_900_000 },
  { entity: "Puebla", padron: 4_700_000 },
];
```

- [ ] **Step 2: Page**

```tsx
// frontend/src/modules/padron/PadronPage.tsx
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppLayout } from "@/components/layout/AppLayout";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { AGE_BANDS, SUMMARY, TOP_ENTITIES } from "./fixtures";

const nf = new Intl.NumberFormat("es-MX");
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export function PadronPage() {
  return (
    <AppLayout title="Padrón / Lista Nominal" crumb="Inteligencia Electoral">
      <PreviewBanner />
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Padrón electoral" value={nf.format(SUMMARY.padron)} />
        <MetricCard label="Lista nominal" value={nf.format(SUMMARY.listaNominal)} />
        <MetricCard label="Cobertura" value={pct(SUMMARY.cobertura)} />
        <MetricCard label="Edad mediana" value={`${SUMMARY.edadMediana} años`} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Distribución por edad y sexo (%)">
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={AGE_BANDS} margin={{ left: -16 }}>
                <XAxis dataKey="band" stroke="#5e6f8f" tick={{ fontSize: 12 }} />
                <YAxis stroke="#5e6f8f" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#0d1422", border: "1px solid #2a3a5c", borderRadius: 10 }} />
                <Bar dataKey="hombres" fill="#4f9cff" radius={[4, 4, 0, 0]} />
                <Bar dataKey="mujeres" fill="#2dd4bf" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Padrón por entidad (top 5)">
          <div className="space-y-2">
            {TOP_ENTITIES.map((e) => (
              <div key={e.entity} className="flex items-center justify-between rounded-lg border border-line bg-bg-sunken px-3 py-2.5">
                <span className="text-sm text-ink">{e.entity}</span>
                <span className="text-sm text-ink-muted">{nf.format(e.padron)}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 3: Build + commit**

Run: `cd frontend && npm run build` → PASS

```bash
git add frontend/src/modules/padron
git commit -m "feat(padron): Padrón / Lista Nominal preview module (W2)"
```

---

### Task 15: AI Analyst / Copiloto (preview, swappable to real)

**Files:**
- Create: `frontend/src/modules/ai-analyst/{fixtures.ts,client.ts}`
- Replace: `frontend/src/modules/ai-analyst/AiAnalystPage.tsx`

- [ ] **Step 1: Fixtures (suggested prompts + canned answers)**

```ts
// frontend/src/modules/ai-analyst/fixtures.ts
export interface CannedAnswer { q: string; a: string; }

export const SUGGESTED: string[] = [
  "¿Qué entidades tienen menor participación?",
  "Resume la cobertura territorial actual.",
  "¿Cuántos eventos de auditoría hubo esta semana?",
];

export const CANNED: CannedAnswer[] = [
  { q: SUGGESTED[0], a: "En los datos de muestra, Veracruz (57%) y Jalisco (59%) están por debajo del promedio nacional (61.2%). Recomendaría priorizar campañas de difusión en esas entidades." },
  { q: SUGGESTED[1], a: "La plataforma tiene cargadas 32 entidades (nivel estatal). Los niveles de distrito y sección están disponibles para ingesta cuando se confirme la fuente cartográfica del SIGE." },
  { q: SUGGESTED[2], a: "La bitácora de auditoría registra los accesos y acciones sensibles de la semana. Consulta el módulo Auditoría & Cumplimiento para el detalle con filtros." },
];
```

- [ ] **Step 2: Client (interface ready for real backend)**

```ts
// frontend/src/modules/ai-analyst/client.ts
import { CANNED } from "./fixtures";

export interface Answer { text: string; sample: boolean; }

/**
 * Preview implementation: returns canned answers. To go live, replace the body
 * with: const { data } = await apiClient.post("/ai/ask", { prompt }); return
 * { text: data.answer, sample: false };
 */
export async function ask(prompt: string): Promise<Answer> {
  const match = CANNED.find((c) => c.q === prompt);
  const text = match?.a ??
    "Respuesta de muestra: conecta un proveedor de modelo (Claude API) para análisis en vivo sobre tus datos reales.";
  return new Promise((resolve) => setTimeout(() => resolve({ text, sample: true }), 350));
}
```

- [ ] **Step 3: Page**

```tsx
// frontend/src/modules/ai-analyst/AiAnalystPage.tsx
import { useState } from "react";

import { AppLayout } from "@/components/layout/AppLayout";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Card } from "@/components/ui/Card";
import { AiIcon } from "@/components/ui/icons";
import { ask, type Answer } from "./client";
import { SUGGESTED } from "./fixtures";

interface Turn { role: "user" | "assistant"; text: string; sample?: boolean; }

export function AiAnalystPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(prompt: string) {
    if (!prompt.trim() || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", text: prompt }]);
    setBusy(true);
    const ans: Answer = await ask(prompt);
    setTurns((t) => [...t, { role: "assistant", text: ans.text, sample: ans.sample }]);
    setBusy(false);
  }

  return (
    <AppLayout title="AI Analyst / Copiloto" crumb="Ciudadanía">
      <PreviewBanner note="Respuestas de muestra · Conecta Claude API para análisis en vivo." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Copiloto" className="lg:col-span-2">
          <div className="flex h-[420px] flex-col">
            <div className="flex-1 space-y-3 overflow-y-auto">
              {turns.length === 0 && (
                <div className="grid h-full place-items-center text-center text-sm text-ink-faint">
                  <div><AiIcon width={28} height={28} className="mx-auto mb-2 text-accent" />Pregúntale al copiloto sobre tus datos.</div>
                </div>
              )}
              {turns.map((t, i) => (
                <div key={i} className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${t.role === "user" ? "ml-auto bg-accent/15 text-ink" : "bg-bg-sunken text-ink-muted"}`}>
                  {t.text}
                  {t.sample && <span className="ml-2 pill border-state-warning/30 bg-state-warning/10 text-state-warning">muestra</span>}
                </div>
              ))}
              {busy && <div className="text-sm text-ink-faint">Pensando…</div>}
            </div>
            <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(input); }}>
              <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Escribe una pregunta…" className="flex-1 rounded-lg border border-line bg-bg-sunken px-3 py-2 text-sm text-ink placeholder:text-ink-faint" />
              <button type="submit" disabled={busy} className="pill border-accent/30 bg-accent/10 text-accent disabled:opacity-40">Enviar</button>
            </form>
          </div>
        </Card>

        <Card title="Preguntas sugeridas">
          <div className="space-y-2">
            {SUGGESTED.map((q) => (
              <button key={q} onClick={() => send(q)} className="w-full rounded-lg border border-line bg-bg-sunken px-3 py-2.5 text-left text-sm text-ink-muted hover:text-ink">
                {q}
              </button>
            ))}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 4: Remove the old dashboard AI placeholder (avoid duplication)**

In `frontend/src/pages/DashboardPage.tsx`, remove the `<AiAnalystPanel />` block and its import (the AI experience now lives in its own module). Run `grep -n AiAnalystPanel frontend/src/pages/DashboardPage.tsx` to find both lines; delete them.

- [ ] **Step 5: Build + commit**

Run: `cd frontend && npm run build` → PASS

```bash
git add frontend/src/modules/ai-analyst frontend/src/pages/DashboardPage.tsx
git commit -m "feat(ai-analyst): copiloto preview module, swappable to Claude API (W2)"
```

---

# Phase W3 — Map robustness

### Task 16: Backend — `level` filter on `/api/maps/areas` (TDD)

**Files:**
- Modify: `backend/app/services/map_service.py`
- Modify: `backend/app/routers/maps.py`
- Create: `backend/tests/test_maps.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_maps.py
"""Tests for the maps areas endpoint and level filter."""

from app.database import get_db
from app.models.electoral_area import AreaLevel, ElectoralArea

from .conftest import auth_headers


def _seed_areas(client):
    # Insert two areas of different levels for the alpha org via the test session.
    gen = get_db.__wrapped__ if hasattr(get_db, "__wrapped__") else None  # not used
    from app.main import app  # noqa
    db = next(app.dependency_overrides[get_db]())
    # Find alpha org id from the seeded admin's token introspection is overkill;
    # query the org directly.
    from app.models.organization import Organization
    from sqlalchemy import select
    org = db.execute(select(Organization).where(Organization.slug == "alpha")).scalar_one()
    db.add_all([
        ElectoralArea(organization_id=org.id, name="Distrito 1", code="D1", level=AreaLevel.DISTRICT),
        ElectoralArea(organization_id=org.id, name="Entidad 1", code="E1", level=AreaLevel.STATE),
    ])
    db.commit()
    db.close()


def test_areas_requires_auth(client):
    assert client.get("/api/maps/areas").status_code == 401


def test_areas_returns_feature_collection(client):
    _seed_areas(client)
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/maps/areas", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) >= 2


def test_areas_level_filter(client):
    headers = auth_headers(client, "admin@alpha.gov")
    resp = client.get("/api/maps/areas?level=district", headers=headers)
    assert resp.status_code == 200, resp.text
    levels = {f["properties"]["level"] for f in resp.json()["features"]}
    assert levels <= {"district"}
```

- [ ] **Step 2: Run RED**

Run: `cd backend && python3 -m pytest tests/test_maps.py -q`
Expected: `test_areas_level_filter` FAILS (filter not implemented; returns all levels).

- [ ] **Step 3: Add `level` to the service**

In `backend/app/services/map_service.py`, change the signature and both branches of `list_areas_geojson`:

```python
def list_areas_geojson(
    db: Session, organization_id: str | None, level: str | None = None
) -> dict[str, Any]:
```

In the PostgreSQL branch, after the `organization_id` filter:

```python
        if level is not None:
            stmt = stmt.where(ElectoralArea.level == level)
```

In the SQLite/else branch, after its `organization_id` filter, add the same two lines (the `stmt` there selects `ElectoralArea`, so `ElectoralArea.level == level` works identically).

Note: `ElectoralArea.level` is an Enum column; comparing to the string value (e.g. `"district"`) works because `AreaLevel` is a `str` enum. To be safe, normalize: `from app.models.electoral_area import AreaLevel` and use `AreaLevel(level)` if `level` is a valid member, else skip the filter:

```python
        if level:
            try:
                stmt = stmt.where(ElectoralArea.level == AreaLevel(level))
            except ValueError:
                pass  # unknown level → no filter
```

Add `from app.models.electoral_area import AreaLevel` to imports (replace the existing `ElectoralArea`-only import line with both).

- [ ] **Step 4: Pass `level` through the router**

In `backend/app/routers/maps.py`, update `list_areas`:

```python
from fastapi import APIRouter, Query  # update import

@router.get("/areas", summary="Electoral areas as GeoJSON")
def list_areas(
    db: DbSession,
    ctx: Tenant,
    level: str | None = Query(None, description="Filter by level (e.g. state, district)"),
) -> dict[str, Any]:
    """Return tenant-scoped electoral areas as a GeoJSON FeatureCollection."""
    return map_service.list_areas_geojson(db, ctx.organization_id, level)
```

- [ ] **Step 5: Run GREEN**

Run: `cd backend && python3 -m pytest -q`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/map_service.py backend/app/routers/maps.py backend/tests/test_maps.py
git commit -m "feat(maps): optional level filter on /api/maps/areas (W3)"
```

---

### Task 17: Frontend maps API — `level` param + sample metric helper

**Files:**
- Modify: `frontend/src/api/maps.ts`
- Modify: `frontend/src/types/maps.ts`

- [ ] **Step 1: Add `level` to `getAreas`**

Replace `getAreas` in `frontend/src/api/maps.ts`:

```ts
export async function getAreas(level?: string): Promise<AreasResponse> {
  const { data } = await apiClient.get<AreasResponse>("/maps/areas", {
    params: level ? { level } : undefined,
  });
  return data;
}
```

- [ ] **Step 2: Add a deterministic sample metric helper to `types/maps.ts`**

Append:

```ts
/** Deterministic sample metric in [0,1] from an area id — clearly labelled
 *  "datos de muestra" in the UI until real per-area metrics exist. */
export function sampleMetric(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return 0.45 + (h % 1000) / 1000 * 0.45; // 0.45–0.90
}
```

- [ ] **Step 3: Build + commit**

Run: `cd frontend && npm run build` → PASS

```bash
git add frontend/src/api/maps.ts frontend/src/types/maps.ts
git commit -m "feat(maps): getAreas level param + sample metric helper (W3)"
```

---

### Task 18: Map components — Legend & AreaDetailPanel

**Files:**
- Create: `frontend/src/components/maps/Legend.tsx`
- Create: `frontend/src/components/maps/AreaDetailPanel.tsx`

- [ ] **Step 1: Legend**

```tsx
// frontend/src/components/maps/Legend.tsx
const STOPS = [
  { c: "#0d3b66", v: "0.45" },
  { c: "#1d6fb8", v: "" },
  { c: "#4f9cff", v: "0.68" },
  { c: "#9ecbff", v: "" },
  { c: "#dcedff", v: "0.90" },
];

export function Legend({ label }: { label: string }) {
  return (
    <div className="absolute bottom-3 left-3 z-10 rounded-lg border border-line bg-panel/90 px-3 py-2 backdrop-blur">
      <div className="mb-1 text-[11px] uppercase tracking-wide text-ink-faint">{label} · muestra</div>
      <div className="flex items-center gap-1">
        {STOPS.map((s, i) => <span key={i} className="h-3 w-7" style={{ background: s.c }} />)}
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-ink-faint"><span>0.45</span><span>0.90</span></div>
    </div>
  );
}
```

- [ ] **Step 2: AreaDetailPanel**

```tsx
// frontend/src/components/maps/AreaDetailPanel.tsx
import type { AreaProperties } from "@/types/maps";

interface Props { area: (AreaProperties & { metric: number }) | null; onClose: () => void; }

export function AreaDetailPanel({ area, onClose }: Props) {
  if (!area) return null;
  return (
    <div className="absolute right-3 top-3 z-10 w-64 rounded-lg border border-line bg-panel/95 p-4 backdrop-blur">
      <div className="flex items-start justify-between">
        <div>
          <div className="eyebrow">{area.level}</div>
          <div className="text-base font-semibold text-ink">{area.name}</div>
          {area.code && <div className="text-xs text-ink-faint">{area.code}</div>}
        </div>
        <button onClick={onClose} className="text-ink-faint hover:text-ink">✕</button>
      </div>
      <div className="mt-3 space-y-2 text-sm">
        <div className="flex justify-between"><span className="text-ink-muted">Métrica (muestra)</span><span className="text-ink">{(area.metric * 100).toFixed(1)}%</span></div>
        <div className="rounded-lg border border-line bg-bg-sunken px-3 py-2 text-xs text-ink-faint">
          Drill-down a distritos/secciones disponible al ingerir niveles inferiores.
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Build + commit**

Run: `cd frontend && npm run build` → PASS

```bash
git add frontend/src/components/maps/Legend.tsx frontend/src/components/maps/AreaDetailPanel.tsx
git commit -m "feat(maps): legend + area detail panel components (W3)"
```

---

### Task 19: MapCanvas — choropleth, hover, click, basemap, fit-bounds

**Files:**
- Modify: `frontend/src/components/maps/MapCanvas.tsx` (full replace)

- [ ] **Step 1: Replace the file**

```tsx
import { useEffect, useRef } from "react";
import maplibregl, { type GeoJSONSource, type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { AreasResponse, AreaProperties } from "@/types/maps";
import { sampleMetric } from "@/types/maps";

export interface WmsOverlay { id: string; tiles: string[]; visible: boolean; }
export type Basemap = "dark" | "satellite";

interface MapCanvasProps {
  areas: AreasResponse | null;
  showAreas: boolean;
  wmsLayers?: WmsOverlay[];
  choropleth: boolean;
  basemap: Basemap;
  fitKey?: number; // bump to trigger fit-to-bounds
  onSelect?: (props: (AreaProperties & { metric: number }) | null) => void;
}

const AREAS_SOURCE = "agora-areas";
const AREAS_FILL = "agora-areas-fill";
const AREAS_LINE = "agora-areas-line";

const RASTER: Record<Basemap, { tiles: string[]; attribution: string; paint: Record<string, number> }> = {
  dark: { tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], attribution: "© OpenStreetMap", paint: { "raster-saturation": -0.85, "raster-brightness-max": 0.85 } },
  satellite: { tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], attribution: "© Esri", paint: { "raster-saturation": 0 } },
};

const styleFor = (b: Basemap): StyleSpecification => ({
  version: 8,
  sources: { base: { type: "raster", tiles: RASTER[b].tiles, tileSize: 256, attribution: RASTER[b].attribution } },
  layers: [{ id: "base", type: "raster", source: "base", paint: RASTER[b].paint as never }],
});

const EMPTY_FC: AreasResponse = { type: "FeatureCollection", features: [] };

// Inject the sample metric into each feature property for data-driven styling.
function withMetric(fc: AreasResponse): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: fc.features.map((f) => ({
      ...f,
      properties: { ...f.properties, metric: sampleMetric(f.properties.id) },
    })),
  } as unknown as GeoJSON.FeatureCollection;
}

const FLAT_FILL: maplibregl.FillLayerSpecification["paint"] = { "fill-color": "#4f9cff", "fill-opacity": 0.18 };
const CHORO_FILL: maplibregl.FillLayerSpecification["paint"] = {
  "fill-opacity": 0.6,
  "fill-color": [
    "interpolate", ["linear"], ["get", "metric"],
    0.45, "#0d3b66", 0.68, "#4f9cff", 0.9, "#dcedff",
  ] as never,
};

export function MapCanvas({ areas, showAreas, wmsLayers = [], choropleth, basemap, fitKey, onSelect }: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const wmsAddedRef = useRef<Set<string>>(new Set());
  const popupRef = useRef<maplibregl.Popup | null>(null);

  // Init once. Basemap change re-inits via key on the wrapper (see Task 20).
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleFor(basemap),
      center: [-102.55, 23.63],
      zoom: 4.2,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;
    popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

    map.on("load", () => {
      readyRef.current = true;
      map.addSource(AREAS_SOURCE, { type: "geojson", data: EMPTY_FC as never });
      map.addLayer({ id: AREAS_FILL, type: "fill", source: AREAS_SOURCE, paint: FLAT_FILL });
      map.addLayer({ id: AREAS_LINE, type: "line", source: AREAS_SOURCE, paint: { "line-color": "#2dd4bf", "line-width": 1.2 } });

      map.on("mousemove", AREAS_FILL, (e) => {
        map.getCanvas().style.cursor = "pointer";
        const f = e.features?.[0];
        if (f && popupRef.current) {
          const p = f.properties as Record<string, unknown>;
          popupRef.current.setLngLat(e.lngLat).setHTML(`<div style="font:12px sans-serif;color:#0d1422"><b>${p.name}</b></div>`).addTo(map);
        }
      });
      map.on("mouseleave", AREAS_FILL, () => { map.getCanvas().style.cursor = ""; popupRef.current?.remove(); });
      map.on("click", AREAS_FILL, (e) => {
        const f = e.features?.[0];
        if (f && onSelect) {
          const p = f.properties as unknown as AreaProperties & { metric: number };
          onSelect({ ...p, metric: Number((p as { metric: number }).metric) });
        }
      });
    });

    return () => { map.remove(); mapRef.current = null; readyRef.current = false; wmsAddedRef.current = new Set(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Data + visibility + choropleth styling.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource(AREAS_SOURCE) as GeoJSONSource | undefined;
      if (src) src.setData(withMetric(areas ?? EMPTY_FC));
      const vis = showAreas ? "visible" : "none";
      if (map.getLayer(AREAS_FILL)) {
        map.setLayoutProperty(AREAS_FILL, "visibility", vis);
        map.setPaintProperty(AREAS_FILL, "fill-color", (choropleth ? CHORO_FILL : FLAT_FILL)["fill-color"] as never);
        map.setPaintProperty(AREAS_FILL, "fill-opacity", (choropleth ? CHORO_FILL : FLAT_FILL)["fill-opacity"] as never);
      }
      if (map.getLayer(AREAS_LINE)) map.setLayoutProperty(AREAS_LINE, "visibility", vis);
    };
    if (readyRef.current) apply(); else map.once("load", apply);
  }, [areas, showAreas, choropleth]);

  // WMS overlays (unchanged behavior).
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      for (const layer of wmsLayers) {
        const id = layer.id;
        if (!wmsAddedRef.current.has(id)) {
          if (!map.getSource(id)) map.addSource(id, { type: "raster", tiles: layer.tiles, tileSize: 256 });
          const beforeId = map.getLayer(AREAS_FILL) ? AREAS_FILL : undefined;
          map.addLayer({ id, type: "raster", source: id, paint: { "raster-opacity": 0.85 } }, beforeId);
          wmsAddedRef.current.add(id);
        }
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", layer.visible ? "visible" : "none");
      }
    };
    if (readyRef.current) apply(); else map.once("load", apply);
  }, [wmsLayers]);

  // Fit to bounds of current areas when fitKey changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !areas || areas.features.length === 0) return;
    const b = new maplibregl.LngLatBounds();
    let any = false;
    for (const f of areas.features) {
      const g = f.geometry as GeoJSON.Geometry | null;
      if (!g) continue;
      const coords = (g as GeoJSON.Polygon | GeoJSON.MultiPolygon).coordinates as number[][][] | number[][][][];
      const flat = JSON.stringify(coords).match(/-?\d+\.\d+/g)?.map(Number) ?? [];
      for (let i = 0; i + 1 < flat.length; i += 2) { b.extend([flat[i], flat[i + 1]]); any = true; }
    }
    if (any) map.fitBounds(b, { padding: 40, maxZoom: 6, duration: 600 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-card border border-line">
      <div ref={containerRef} className="absolute inset-0" />
    </div>
  );
}
```

Note on basemap switching: re-creating the MapLibre style at runtime is fiddly; the simplest robust approach is to remount `MapCanvas` when the basemap changes via a React `key` (done in Task 20). The `basemap` prop is read on init.

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: PASS. If `tsc` complains about MapLibre paint expression typing, the `as never` casts above contain them; keep them.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/maps/MapCanvas.tsx
git commit -m "feat(maps): choropleth, hover, click-select, basemap, fit-bounds (W3)"
```

---

### Task 20: MapExplorerPage — wire controls (level, choropleth, basemap, search, detail)

**Files:**
- Modify: `frontend/src/pages/MapExplorerPage.tsx`

- [ ] **Step 1: Read the full current file**

Run: `cat frontend/src/pages/MapExplorerPage.tsx` — note how `MapCanvas`, `LayerPanel`, state, and the layout are composed; preserve the WMS handling and `LayerPanel`.

- [ ] **Step 2: Add state + controls and pass new props to MapCanvas**

Apply these changes:
1. Imports: add
```tsx
import { useMemo } from "react"; // if not already imported
import { AreaDetailPanel } from "@/components/maps/AreaDetailPanel";
import { Legend } from "@/components/maps/Legend";
import type { AreaProperties } from "@/types/maps";
import type { Basemap } from "@/components/maps/MapCanvas";
```
2. State: add inside the component
```tsx
const [level, setLevel] = useState<string>("");        // "" = all
const [choropleth, setChoropleth] = useState(true);
const [basemap, setBasemap] = useState<Basemap>("dark");
const [selected, setSelected] = useState<(AreaProperties & { metric: number }) | null>(null);
const [search, setSearch] = useState("");
const [fitKey, setFitKey] = useState(0);
```
3. Re-fetch areas when `level` changes: in the existing data-loading effect, additionally (or in a new effect) call `getAreas(level || undefined).then(setAreas)` whenever `level` changes. Add:
```tsx
useEffect(() => {
  getAreas(level || undefined)
    .then(setAreas)
    .catch(() => setAreas({ type: "FeatureCollection", features: [] }));
}, [level]);
```
4. Search filter: compute the areas passed to the canvas:
```tsx
const filteredAreas = useMemo(() => {
  if (!areas) return areas;
  if (!search.trim()) return areas;
  const q = search.toLowerCase();
  return { ...areas, features: areas.features.filter((f) => f.properties.name.toLowerCase().includes(q)) };
}, [areas, search]);
```
5. Toolbar UI: above/over the map, add a control row (place inside the map column, before `<MapCanvas>`):
```tsx
<div className="mb-3 flex flex-wrap items-center gap-2">
  <select value={level} onChange={(e) => setLevel(e.target.value)} className="rounded-lg border border-line bg-bg-sunken px-2 py-1.5 text-sm text-ink">
    <option value="">Todos los niveles</option>
    <option value="state">Entidad</option>
    <option value="district">Distrito</option>
    <option value="municipality">Municipio</option>
  </select>
  <select value={basemap} onChange={(e) => setBasemap(e.target.value as Basemap)} className="rounded-lg border border-line bg-bg-sunken px-2 py-1.5 text-sm text-ink">
    <option value="dark">Mapa oscuro</option>
    <option value="satellite">Satélite</option>
  </select>
  <label className="flex items-center gap-2 text-sm text-ink-muted">
    <input type="checkbox" checked={choropleth} onChange={(e) => setChoropleth(e.target.checked)} /> Coropleta
  </label>
  <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar área…" className="rounded-lg border border-line bg-bg-sunken px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint" />
  <button onClick={() => setFitKey((k) => k + 1)} className="pill border-line text-ink-muted">Encadrar</button>
</div>
```
6. Map wrapper: wrap `MapCanvas` so it remounts on basemap change and overlays Legend + detail panel:
```tsx
<div className="relative h-[520px]">
  <MapCanvas
    key={basemap}
    areas={filteredAreas}
    showAreas={/* keep existing showAreas logic */ true}
    wmsLayers={/* keep existing wms overlays array */ []}
    choropleth={choropleth}
    basemap={basemap}
    fitKey={fitKey}
    onSelect={setSelected}
  />
  {choropleth && <Legend label="Participación" />}
  <AreaDetailPanel area={selected} onClose={() => setSelected(null)} />
</div>
```
Keep the existing `LayerPanel` and WMS wiring exactly as-is; only the `MapCanvas` invocation and the surrounding wrapper change. Preserve whatever `showAreas` and `wmsLayers` values the current file passes.

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: PASS. Resolve any unused-variable `tsc` errors by removing leftover state the refactor replaced.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/MapExplorerPage.tsx
git commit -m "feat(maps): level/basemap/choropleth/search controls + detail panel (W3)"
```

---

### Task 21: Final verification & deploy

- [ ] **Step 1: Full backend test suite**

Run: `cd backend && python3 -m pytest -q`
Expected: PASS (≥ 27 prior + new audit + maps tests).

- [ ] **Step 2: Frontend build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: Push (triggers Railway deploy)**

```bash
git push origin main
```

- [ ] **Step 4: Verify on production after deploy SUCCESS**

```bash
BASE="https://agora-gobtech.up.railway.app"
TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" -d '{"email":"ecg@atlastech.mx","password":"<admin-password>"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s "$BASE/api/audit?limit=3" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
curl -s "$BASE/api/maps/areas?level=state" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json;print('state features:', len(json.load(sys.stdin)['features']))"
```
Expected: audit returns a paginated page; areas?level=state returns 32 features. Poll `railway deployment list --service Agora` until newest is SUCCESS before testing (see project memory for the link command + admin password location).

---

## Self-Review notes (addressed)

- **Spec coverage:** registry/states/badges (T1–T2), PreviewBanner (T3), ComingSoonPage + 6 stubs (T4, T1 data), sidebar/route refactor (T5–T6), Auditoría real backend+frontend (T8–T12), Resultados (T13), Padrón (T14), AI Analyst swappable (T15), map level filter (T16–T17), interactivity/choropleth/controls (T18–T20), honesty banners/legend ("muestra") throughout, testing (T11, T16), phased W1/W2/W3.
- **Type consistency:** `ModuleDef`/`ModuleState`/`SECTION_*` defined in T1 and consumed in T2/T5/T6; `AreaProperties & { metric }` flows MapCanvas→AreaDetailPanel; `Basemap` exported from MapCanvas and imported in MapExplorerPage; `getAreas(level?)` matches router `level` query.
- **Out of scope** kept out: real pipelines, live Claude wiring, Alembic, rate-limiting.
