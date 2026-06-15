# Ágora — External Intelligence Sources & Module Enrichment — Design

**Date:** 2026-06-15
**Status:** Approved (design); pending implementation plan
**Author:** Emmanuel Campos Genaro + Claude

## 1. Goal

Two complementary thrusts, both approved by the user:

1. **New intelligence modules** powered by additional external APIs (starting with token-free, reachable sources: **DataMéxico**, **World Bank**), behind a robust backend proxy, plus an economic layer on the map. Token-gated sources (INEGI, Banxico) are built as **preview now, pluggable later**.
2. **Enrich the existing modules** — more KPIs, more chart types, denser "big-screen" detail so the platform looks **advanced, ostentatious, highly detailed** — while preserving the all-black command-center aesthetic and the project's honesty rule (real data where it exists, labelled sample otherwise).

## 2. Context (current state)

- Deployed all-black "DataV" command center on Railway (`https://agora-gobtech.up.railway.app`). FastAPI + PostgreSQL/PostGIS + Vite/React/TS/Tailwind, single service.
- Real data we control: `electoral_areas` (32 states), `audit_logs` (action/actor/created_at/meta), `users`, `organizations`.
- Real modules: Dashboard, Map Explorer, Analytics (audit activity), **Territorios** (areas by level), **Auditoría**. Previews: Resultados, Padrón, AI Analyst. 6 → now 5 coming-soon stubs.
- Robustness foundation already in place: `useAsync` hook + `DataState` (loading/error+retry/empty); premium primitives (`PageHeader`, `MetricCard` with countTo/tone/trend, `AnimatedNumber`, `Sparkline`, `card-premium`, `hud-corners`).
- External INE sources are unreliable: apielectoral.mx (DNS dead), datos.gob.mx (broken SSL chain). Lesson: **fetch external data server-side, with retries + graceful degradation**.

## 3. Architecture decision: external-source proxy framework (Approach A)

Chosen over per-module bespoke endpoints (B) and browser-direct fetch (C).

**Backend** — a small, generic intelligence proxy:
- Router `backend/app/routers/intel.py` exposing typed, purpose-built endpoints per source (NOT a blind open proxy — each endpoint validates/normalizes params and shapes the response), e.g.:
  - `GET /api/intel/datamexico/economy?level=state&measure=...`
  - `GET /api/intel/worldbank/indicator?code=NY.GDP.MKTP.CD`
- Integrations under `backend/app/integrations/intel/` (one module per source: `datamexico.py`, `worldbank.py`), reusing the existing `base.py` httpx wrapper (timeouts, bounded retries) — server-side fetch eliminates CORS and lets us control TLS.
- **In-process TTL cache** (small dict with timestamp, e.g. 15 min) so repeated requests don't hammer upstreams and survive brief upstream blips.
- Uniform error envelope (Golden Rule #8). On upstream failure the endpoint returns a 502 with a clear message; the frontend `DataState` renders error+retry. Tenant-scoping: these are public reference datasets (not tenant data) but still require auth (`Tenant` dep).

**Frontend** — a typed data layer (`src/api/intel.ts` + `src/types/intel.ts`) consumed via `useAsync`, every module wrapped in `DataState` so a dead upstream degrades gracefully (or falls back to a labelled preview).

**Feasibility note (verify first):** reachability of DataMéxico/World Bank from the Railway container must be probed during implementation (like the CARTO check) before claiming "real". World Bank (`api.worldbank.org/v2`, JSON, reliable, no token) is the safe anchor; DataMéxico (`api.datamexico.org` Tesseract OLAP) is higher-value but reachability/CORS/query-shape must be confirmed — if it fails, that module degrades to preview with the same UI.

## 4. New modules

### 4.1 Economía Territorial — DataMéxico `(real via proxy; preview fallback)`
- Backend `datamexico.py` + `/api/intel/datamexico/*`: economic indicators by entity (e.g. GDP, employment, trade, economic complexity).
- Frontend module page: KPI tiles, an **economic choropleth layer on the existing map** (entity-level metric driving fill via the established `MapCanvas` choropleth, with a metric selector), a sortable entity table, and trend charts.
- Synergy: cross economic data with our electoral territories.

### 4.2 Indicadores Nacionales — World Bank `(real via proxy)`
- Backend `worldbank.py` + `/api/intel/worldbank/indicator`: national time series for Mexico (GDP, population, poverty headcount, unemployment, inflation).
- Frontend module: a grid of indicator cards each with a real multi-year line/area chart + latest value + delta; an indicator picker.

### 4.3 Token-gated previews (pluggable) `(preview now)`
- **Demografía & Censo (INEGI)**, **Unidades Económicas (DENUE)**, **Macro-financiero (Banxico SIE)** — built as preview modules with labelled sample fixtures and a `client.ts` seam so swapping to the real proxy endpoint is mechanical once a token is provided. Registered with `preview` state + PreviewBanner.

### 4.4 Índice Cívico-Territorial `(later spec — noted, not in first implementation)`
- A synthesis module overlaying participation + socioeconomic layers per territory. Deferred to a follow-up spec.

## 5. Enrichment of existing modules ("advanced / ostentatious / detailed")

Densify the existing modules with more KPIs and chart variety, in the all-black big-screen style, **honesty preserved** (real where data exists; sample clearly labelled in previews).

**Reusable additions (foundation):**
- New chart primitives (Recharts-based, cyan/amber dark palette): `Donut`, `RadialGauge`, `StackedBars`, `Heatmap` (calendar/hour grid), `MiniLine`/multi-series. Each its own focused component under `src/components/charts/`.
- A `StatTicker` strip (animated marquee of live stats) and a `KpiTile` variant with sparkline + delta + gauge.

**Per module (real data unless noted):**
- **Dashboard (real):** add a live stat ticker; more KPI tiles (areas, orgs, users, sources, audit-events-today, coverage %); a **radial gauge** (coverage), an **audit activity heatmap** (last 14–30 days, real), a sources-health panel, refined hero. 
- **Analytics (real):** expand from one chart to a dashboard — activity by **action type** (donut/stacked bar), by **top actors** (bar), an **hourly/daily heatmap**, cumulative line — all aggregated from real `audit_logs`. Requires backend: extend `analytics_service` with `events_by_action`, `events_by_actor`, `events_by_hour/day` (tenant-scoped).
- **Auditoría (real):** add summary charts above the table — events by action (donut), over time (sparkline/line), top actors — from real data.
- **Territorios (real):** richer per-area detail, level distribution chart, density stats.
- **Resultados (preview):** add turnout **gauge**, party **treemap/donut**, historical **multi-line**, margin distribution — expanded fixtures, all under PreviewBanner.
- **Padrón (preview):** more gauges, coverage choropleth, additional breakdowns — expanded fixtures, labelled.

**Backend work for real enrichment:** extend `analytics_service` with the new tenant-scoped aggregations (by action/actor/time) + endpoints (or fields on `/analytics/overview`), with tests. No fabricated data.

## 6. Honesty rules (unchanged, reaffirmed)

- Real modules/charts use only real data (DB or live upstream); on upstream failure → `DataState` error+retry or labelled preview.
- Preview modules keep `PreviewBanner` and sample fixtures; sample metrics labelled "muestra".
- Animated counters animate to real values; no fabricated trends on metrics lacking a real series.

## 7. Testing

- Backend: tests for `intel` endpoints (success shape + graceful 502 on upstream error, using a stubbed client), and for the new `analytics_service` aggregations (tenant-scoped, correct grouping). All existing tests stay green.
- Frontend: `npm run build` (tsc strict) must pass; new chart components type-checked.

## 8. Scope & phasing (decomposed)

Large — split into sequential implementation specs/plans:

- **Phase 1 (this spec's first plan): Proxy framework + World Bank module + chart primitives + real Analytics/Dashboard enrichment.** Highest-certainty real value (World Bank reliable; audit aggregations real). Establishes the chart library reused everywhere.
- **Phase 2: DataMéxico module + economic map layer** (after reachability probe).
- **Phase 3: Enrich Resultados/Padrón previews + token-gated preview modules (INEGI/DENUE/Banxico).**
- **Phase 4: Índice Cívico-Territorial** (own spec).

Each phase is independently deployable.

## 9. Out of scope (explicit)

- Wiring token-gated APIs to live data (built as pluggable previews until keys provided).
- AI Analyst live wiring (parked).
- Reviving apielectoral.mx / datos.gob.mx (upstreams broken).

## 10. Non-functional

- Follow established patterns (all-black tokens, `useAsync`/`DataState`, `PageHeader`, module registry, tenant-scoping via `ctx.is_superadmin`, lazy routes, golden error envelope, server-side fetch for external data).
- Keep files focused; chart primitives small and reusable; integrations one-per-source.
