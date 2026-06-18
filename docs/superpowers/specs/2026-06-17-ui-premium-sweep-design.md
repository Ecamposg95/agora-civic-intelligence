# UI Premium Sweep — Design Spec

**Date:** 2026-06-17
**Status:** Approved (direction B) — pending spec review
**Scope:** Frontend only (`frontend/src`). No backend changes, no new data sources.
**Owner:** Ágora Civic Intelligence (Atlas Tech)

## 1. Goal

Bring every module of the platform up to the visual and UX standard of the
premium core pages (Dashboard, Map Explorer, Analytics), addressing four goals
at once:

1. **Consistency & polish** — uniform page shell, spacing rhythm, cards,
   empty/loading/error states across all ~28 modules.
2. **Wow-factor / demo** — entrance animations, micro-interactions, stronger
   data-viz, HUD/aura treatment where it earns its place.
3. **Accessibility & UX** — focus-visible rings, keyboard navigation, ARIA on
   tabs/tables, responsive layouts without hardcoded heights.
4. **Operational productivity** — sortable/paginated tables, consistent
   filters, predictable interaction patterns.

**Approach:** Foundation-first, then a module-by-module sweep (direction B).
A short Phase 0 hardens shared primitives so every subsequent module inherits
consistency and accessibility for free; the per-module sweep then costs ~1/3 of
a from-scratch rebuild and cannot drift.

## 2. Non-Goals (YAGNI)

- No backend/API changes; no new data sources or endpoints.
- No real AI wiring (per standing user directive — AI Analyst stays
  frontend-only, no Claude API).
- No re-theming (the all-black DataV palette stays; we consume existing tokens,
  not redefine them).
- No global navigation redesign / command palette in this effort (can be a
  follow-up; explicitly out of scope here to keep the sweep focused).
- No conversion of `preview`/`soon` modules into real data modules — that is the
  separate file-ingestion pipeline effort.

## 3. Data Honesty Constraints (project rule — non-negotiable)

- KPIs and charts render **only real series**; never fabricated numbers.
- `preview` modules keep their `PreviewBanner` and clearly-labelled sample
  fixtures. Polishing them visually must NOT remove the "muestra" labelling.
- Real modules with an empty DB show an honest empty state
  ("Ingesta pendiente"), never fake placeholder data.
- No voter turnout / participation numbers are invented.

## 4. Architecture: Shared Primitives (Phase 0)

All primitives live under `frontend/src/components/ui/` (or `charts/`/`constants/`)
and consume existing Tailwind tokens. Each is independently testable and has one
clear responsibility.

### 4.1 Focus & interaction baseline (CSS, `index.css`)
- Add `focus-visible:ring-1 focus-visible:ring-accent/50 focus-visible:ring-offset-0 outline-none`
  to the `.btn` base mixin (so `.btn-primary`/`.btn-ghost` inherit it).
- Add a shared `.focus-ring` utility for non-button interactive elements
  (NavLinks, tab buttons, table sort headers, icon buttons).
- Apply `.focus-ring` to Sidebar `NavLink`, Topbar icon buttons, and `Modal`
  close button.
- Use `:focus-visible` (not `:focus`) so mouse clicks don't show rings but
  keyboard nav does.

### 4.2 `<SegmentedControl>` / `<Tabs>` (`components/ui/SegmentedControl.tsx`)
Replaces the ad-hoc segmented buttons in Resultados, Padrón, Map Explorer, etc.
- Props: `options: {id, label, icon?}[]`, `value`, `onChange`, `size?`.
- ARIA: `role="tablist"` on container, `role="tab"` + `aria-selected` on each;
  roving-tabindex with ArrowLeft/ArrowRight/Home/End keyboard nav.
- Visual: active = `bg-accent/10 text-accent ring-1 ring-accent/25`; focus ring.
- **What it does:** single source of truth for the "segmented view switch"
  pattern. **Depends on:** tokens only.

### 4.3 `<DataTable>` (`components/ui/DataTable.tsx`)
Replaces the hand-rolled tables (Users, Auditoría, IEEM, Padrón, etc.).
- Generic over a row type; column defs `{key, header, render?, sortable?, align?}`.
- Sortable headers with ▲▼ indicator + `aria-sort`; click toggles asc/desc.
- Sticky header (`bg-bg-sunken/80 backdrop-blur`), zebra/hover rows, focus ring
  on sortable headers.
- Built-in pagination (page size prop, range indicator "1–20 de 7053").
- Built-in empty state (delegates to `DataState` empty styling).
- **Mobile fallback:** below `md`, renders each row as a stacked label/value
  card instead of a horizontally-scrolling table (`renderCard?` opt-in;
  default derives from columns).
- **What it does:** one accessible, responsive, sortable table everywhere.
  **Depends on:** `DataState` (empty), tokens.

### 4.4 `<SkeletonCard>` & DataState hardening (`components/ui/`)
- New `<SkeletonCard lines?={n} />` (and `<SkeletonRows>`), replacing inline
  `animate-pulse` divs (e.g. `DenuePage.tsx:48-56`).
- `DataState` gains an explicit `empty` prop alias and documented usage; the
  existing API (loading/error/isEmpty/onRetry/skeleton/emptyMessage) is kept
  backward-compatible. Default empty copy parameterized for "Ingesta pendiente".
- **Retry correctness:** audit each `useAsync` call site so `onRetry` actually
  refetches (the audit flagged a possible stale-closure on IEEM's `reload`).

### 4.5 `constants/ui.ts` (new)
Single home for values currently duplicated across pages:
- `CHART_TOOLTIP_STYLE` (replaces hardcoded `{background:"#06090c",border:...}`
  in Resultados/Padrón/ParticipationChart).
- `CHART_PALETTE` (cyan→amber→teal ramp pulled from tokens) for Recharts series.
- `KIND_BADGE` (source kinds — dedupe Dashboard + Sources) and `ROLE_BADGE`
  (user roles — from Users).
- `PANEL_HEIGHTS` responsive height helpers (e.g. `mapTall`, `chartMd`) to
  replace fixed `h-[600px]`/`h-[440px]`.

### 4.6 "Premium page recipe" (documented checklist)
A documented, repeatable definition of "done" for a module page. Encoded in this
spec (§6) and referenced by every module task.

## 5. Per-Module Sweep (Phase 1+)

Modules are swept in priority order by current polish tier (from the
2026-06-17 audit). Each module passes through the **same checklist** (§6).

**Tier 3 — draft → premium (highest impact, do first):**
`ai-analyst`, `configuracion`, `busqueda`, `organizaciones`, `indice`,
`worldbank`.

**Tier 2 — standard → premium:**
`resultados`, `padron`, `ieem`, `territorios`, `economia`, `denue`, `banxico`,
`demografia`, `auditoria`, `historial`, `reportes`.

**Core — fine-tuning only (wow-factor pass):**
`DashboardPage`, `MapExplorerPage`, `AnalyticsPage`, plus `LoginPage`,
`UsersPage`, `SourcesPage`, `OrganizationSettingsPage`, `ProfilePage`,
`ChangePasswordPage` — already strong; apply only the shared primitives
(focus rings, DataTable where applicable) and small consistency fixes.

**`soon` stubs** (`candidaturas`, `sentimiento`, `participacion`, `riesgo`):
`ComingSoonPage` gets one polish pass; individual stubs unchanged.

### Module-specific notes (beyond the checklist)
- **ai-analyst:** remove hardcoded `h-[440px]`; responsive 2-col→1-col; richer
  empty/idle state for the copilot panel; keep "preview / no real connection".
- **configuracion:** wrap integration rows in DataState; add PreviewBanner tone
  consistency; status board uses shared badges.
- **busqueda:** clear grouped-results layout + explicit "0 resultados" empty
  state; result rows keyboard-navigable.
- **map-explorer / ai-analyst / dashboard mini-map:** replace fixed heights with
  `PANEL_HEIGHTS` responsive values.
- **tables (users/auditoría/ieem/padrón/territorios):** migrate to `<DataTable>`.

## 6. The Premium Page Checklist (definition of done per module)

Every swept module must satisfy:

1. **Header** — uses `<PageHeader>` (eyebrow + title + gradient accent +
   subtitle); auras present on hero. `preview` modules render `<PreviewBanner>`
   directly under the header.
2. **KPI/status strip** — `<MetricCard>` with `<AnimatedNumber>` and
   `<Sparkline>` **only where a real series exists**; otherwise static labels.
3. **Async states** — every data fetch wrapped in `<DataState>`
   (skeleton / error+working retry / honest empty). No silent failures.
4. **Tabs / segmented views** — use `<SegmentedControl>` (ARIA + keyboard).
5. **Tables** — use `<DataTable>` (sortable, paginated, mobile card fallback).
6. **Layout** — responsive grids; NO hardcoded pixel heights (use
   `PANEL_HEIGHTS`); consistent section gap rhythm (`gap-4`/`mb-6`).
7. **Accessibility** — all interactive elements have `:focus-visible` rings and
   labels/roles; color contrast respects tokens.
8. **Charts** — use `CHART_TOOLTIP_STYLE` + `CHART_PALETTE`; no inline hex.
9. **Motion** — content blocks enter with `reveal`/`fade-up`
   (respecting `prefers-reduced-motion`, already guarded globally).
10. **Honesty** — preview labelling intact; no fabricated data.

## 7. Error Handling & Edge Cases

- Failed external sources (the known-down INE/DataMéxico/CKAN) must degrade to
  `DataState` error with a working retry, never a blank or crashed view.
- Empty real datasets (DB not yet ingested) → "Ingesta pendiente" empty state.
- `DataTable` with 0 rows → empty state; with 1 page → no pagination chrome.
- Reduced-motion users: all entrance animations already collapse via the
  global `prefers-reduced-motion` guard in `index.css`.
- Mobile: every table degrades to cards; every fixed-height panel uses a
  responsive scale; sidebar drawer behavior unchanged.

## 8. Testing & Verification

- **Build:** clean `tsc` + `vite build` after each phase (remove
  `*.tsbuildinfo`/`dist` first — incremental cache has given false errors).
- **Manual:** `cd frontend && npm run dev -- --host`; verify each swept module
  at desktop + a narrow (≤640px) viewport; tab through with keyboard to confirm
  focus rings and tab/table nav.
- **Regression guard:** core pages (Dashboard/Map/Analytics) must look
  unchanged except for the additive focus rings.
- **A11y spot-check:** keyboard-only pass on SegmentedControl, DataTable
  headers, and Sidebar; verify `aria-selected`/`aria-sort` present.
- No backend tests affected (frontend-only effort).

## 9. Rollout / Sequencing

- **Phase 0** (foundation): build §4 primitives, land focus-ring baseline,
  migrate ONE reference page (UsersPage → DataTable, a Tier-2 with a real table)
  to prove the primitives end-to-end. One clean build + commit.
- **Phase 1** (Tier 3 modules), **Phase 2** (Tier 2 modules), **Phase 3**
  (core fine-tuning + ComingSoon). Each phase: clean build + commit + deploy
  via GitHub push (`railway up` fails for this project).
- Parallel-agent pattern (proven in this repo): agents own disjoint module
  folders, do NOT touch shared primitives/registry/commit; a controller wires
  shared changes, does one clean build, commits, deploys. Phase 0 primitives
  must land BEFORE module agents start (they depend on them).

## 10. Open Questions

None blocking. Command palette / global-nav redesign deferred to a possible
follow-up effort (out of scope here).
