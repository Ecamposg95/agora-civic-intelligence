# Ágora — Platform Modules Demo & Map Robustness — Design

**Date:** 2026-06-15
**Status:** Approved (design); pending implementation plan
**Author:** Emmanuel Campos Genaro + Claude

## 1. Goal

Expand Ágora from its current working MVP into a **demo of the full platform
vision**: introduce many new modules — not all functional — so a viewer
understands what Ágora will become, and **robustify the Map Explorer** into a
genuinely interactive territorial-intelligence surface.

Honesty is a hard constraint: real data where it exists, clearly-labelled
sample data where it does not. Nothing fabricated may contaminate the real KPIs
already shipped on the dashboard.

## 2. Context (current state)

- Deployed and functional on Railway (`https://agora-gobtech.up.railway.app`).
  FastAPI + PostgreSQL/PostGIS + Vite/React/TS/Tailwind, single service.
- Active modules: Command Center (dashboard), Map Explorer (MapLibre + WMS +
  32 real states), Activity Analytics (real), Sources, Users, Organization.
- Sidebar (`frontend/src/components/layout/Sidebar.tsx`) already has section
  labels and a disabled "AI Analyst — Soon" pattern to build on.
- Routes are lazy-loaded in `frontend/src/App.tsx` behind `RequireAuth`.
- Real data available: `electoral_areas` (32 states), `audit_logs`,
  `organizations`, `users`. No padrón/turnout/results pipeline yet.
- Backend INE integrations exist (CKAN, Candidaturas MX, SIGE cartografía,
  PREP) under `backend/app/integrations/ine/`.

## 3. Architecture decision: hybrid by data-reality

Chosen approach **B (hybrid)**:

- **Real** where data exists today: **Auditoría & Cumplimiento** (audit_logs)
  and **Map** enhancements (real 32 states).
- **Preview** (sample data, clearly labelled) where no pipeline exists:
  **Resultados Electorales**, **Padrón / Lista Nominal**, **AI Analyst**.
- **Coming-soon** stubs for the remaining vision modules.

Rejected: A (all frontend mock — wastes real audit data, less credible);
C (backend mock endpoints for everything — more work and fabricates data in the
backend, undermining the now-real analytics).

## 4. Module taxonomy & states

Every module has one of three states, shown as a `ModuleBadge`:

| State | Meaning | Badge |
|-------|---------|-------|
| `active` | Real data, fully functional | (no badge / "Activo") |
| `preview` | Realistic UI with **sample data** | "Preview" + `PreviewBanner` on the page |
| `soon` | Not built; describes the vision | "Pronto" (nav item routes to `ComingSoonPage`) |

### Sidebar sections (target)

- **Plataforma**: Command Center, Map Explorer, Activity Analytics, Fuentes de datos `(active)`
- **Inteligencia Electoral**: Resultados Electorales `(preview)`, Padrón / Lista Nominal `(preview)`, Candidaturas `(soon)`, Territorios & Secciones `(soon)`
- **Ciudadanía**: AI Analyst / Copiloto `(preview)`, Sentimiento Ciudadano `(soon)`, Participación Ciudadana `(soon)`, Alertas & Riesgo Electoral `(soon)`
- **Gobernanza**: Auditoría & Cumplimiento `(active)`, Reportes Ejecutivos `(soon)`
- **Administración**: Usuarios, Organización `(active, role-gated as today)`

## 5. Module registry (frontend)

A central registry `frontend/src/modules/registry.ts` is the single source of
truth. Each entry:

```ts
interface ModuleDef {
  key: string;
  path: string;            // route path
  label: string;
  section: "plataforma" | "inteligencia" | "ciudadania" | "gobernanza" | "administracion";
  icon: IconComponent;
  state: "active" | "preview" | "soon";
  roles?: UserRole[];      // optional gating (e.g. admin-only)
  element?: LazyComponent; // for active/preview; soon → ComingSoonPage with copy
  soon?: { summary: string; features: string[]; dataSource: string };
}
```

- `Sidebar` renders sections by iterating the registry (role-filtered).
- `App.tsx` builds `<Route>`s from the registry (lazy). `soon` modules route to
  a shared `ComingSoonPage` fed by the entry's `soon` copy.
- Adding a module = one registry entry.

### Shared components

- `ModuleBadge` — pill rendering the state.
- `PreviewBanner` — top-of-page ribbon: "Datos de muestra · Preview de la plataforma".
- `ComingSoonPage` — hero (label + icon), value-prop summary, feature list,
  "Fuente de datos prevista" note. Consistent across all `soon` modules.

## 6. Flagship preview modules

All preview modules read from local fixtures under
`frontend/src/modules/<name>/fixtures.ts` and show a `PreviewBanner`. Fixtures
are plausible Mexican electoral sample data, structured to mirror a future API
shape so swapping to real endpoints is mechanical.

### 6.1 Resultados Electorales `(preview)`
- KPI cards: participación nacional, casillas computadas %, partido líder.
- Party result bars (vote share by party) with party colors.
- Choropleth mini-map of Mexico colored by leading party / turnout (reuses the
  map component + sample per-state metric).
- Table: results by entidad (turnout, winner, margin).

### 6.2 Padrón / Lista Nominal `(preview)`
- KPI cards: padrón total, lista nominal, % cobertura, edad mediana.
- Population pyramid (age × sex).
- Distribution by entidad (bar chart) and by sex (donut).

### 6.3 AI Analyst / Copiloto `(preview)`
- Chat-style panel with suggested prompts (e.g. "¿Qué distritos tienen menor
  participación?").
- Canned, realistic assistant responses keyed to the suggested prompts.
- **Structured for real wiring**: a `frontend/src/modules/ai-analyst/client.ts`
  with a `ask(prompt): Promise<Answer>` interface that currently returns canned
  answers; swapping to a real backend `/api/ai/ask` (Claude API) is a follow-up,
  not in this scope. Banner notes "Respuestas de muestra".

### 6.4 Auditoría & Cumplimiento `(active — REAL)`
- **Backend**: new router `backend/app/routers/audit.py` →
  `GET /api/audit` (tenant-scoped, paginated, filter by `action`, date range),
  backed by `audit_service.list_events(db, ctx, …)`. Superadmin sees all;
  others see their org. Reuses existing `Page`/pagination utilities.
- **Frontend**: audit log table (timestamp, actor, action, entity), filters,
  and a compliance panel derived from real state (audit coverage, # events,
  governance posture). Admin/superadmin-gated.
- Tests: `backend/tests/test_audit.py` (auth required, tenant scoping,
  pagination shape, action filter).

## 7. Coming-soon modules

`Candidaturas`, `Territorios & Secciones`, `Sentimiento Ciudadano`,
`Participación Ciudadana`, `Alertas & Riesgo Electoral`, `Reportes Ejecutivos`
— each a registry entry with `soon` copy rendered by `ComingSoonPage`. No
backend.

## 8. Map robustness (real, over the 32 states)

Enhancements to `MapExplorerPage` / map components:

1. **Interactivity**: click a feature → right-hand detail panel (name, code,
   level, child drill-down placeholder); hover tooltip; legend.
2. **Thematic choropleth**: metric selector + color scale. Until real per-area
   metrics exist, color by a clearly-labelled **sample metric** (e.g. sample
   participación) carried as a feature property; legend states "datos de
   muestra".
3. **Controls & UX**: basemap switch (dark / satellite), area search box,
   fit-to-bounds, zoom controls.
4. **More layers**: a **level selector** (entidad / distrito / municipio) wired
   to `/api/maps/areas?level=`. Backend gains an optional `level` filter.
   Optionally ingest **one additional real layer** (municipios or 300 federal
   districts) via the established `railway ssh … ingest_ine.py cartografia`
   pattern if a clean GeoJSON source is available; otherwise the selector shows
   only populated levels and others read "sin datos".

Backend change: `GET /api/maps/areas` accepts optional `level` query param
(filters `ElectoralArea.level`); default returns all (current behavior).

## 9. Data & honesty rules

- Preview modules: every page shows `PreviewBanner`; charts read from
  `fixtures.ts`; no preview value is ever sent to a real endpoint.
- The real dashboard analytics (already shipped) is untouched.
- Choropleth sample metrics are labelled in the legend.
- Auditoría and Map are the credibility anchors (genuinely real).

## 10. Testing

- Backend: `test_audit.py` (new), extend `test_maps`-style coverage for the
  `level` filter on `/api/maps/areas`. All existing tests stay green.
- Frontend: `npm run build` (tsc) must pass — the registry, new pages, and map
  components are type-checked. No new test framework introduced.

## 11. Scope & phasing (3 workstreams)

- **W1 — Framework & stubs**: module registry, `ModuleBadge`, `PreviewBanner`,
  `ComingSoonPage`, sidebar/route refactor, 6 coming-soon modules.
- **W2 — Flagship modules**: Auditoría (real backend + UI), Resultados, Padrón,
  AI Analyst (previews + fixtures).
- **W3 — Map robustness**: interactivity, choropleth, controls, level selector +
  optional extra layer ingest.

Each workstream is independently deployable. Implementation plan (writing-plans)
will sequence tasks within and across workstreams.

## 12. Out of scope (explicit)

- Real data pipelines for padrón / results / sentiment.
- Wiring AI Analyst to a live Claude API (left as a 1-step follow-up).
- Alembic migration baseline, login rate-limiting, token refresh (tracked
  separately).
- Mobile-specific layouts beyond the existing responsive grid.

## 13. Non-functional

- Follow existing patterns (dark theme, `Card`/`MetricCard`/pill styles,
  tenant-scoping via `ctx.is_superadmin`, lazy routes, golden error envelope).
- Keep files focused; new modules live under `frontend/src/modules/<name>/`.
- Bundle: new heavy deps avoided; reuse Recharts/MapLibre already bundled.
