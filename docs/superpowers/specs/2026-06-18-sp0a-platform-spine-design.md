# SP0a — Platform Spine — Design Spec

**Date:** 2026-06-18
**Status:** Approved (design) — pending spec review
**Parent program:** `docs/superpowers/specs/2026-06-18-electoral-intelligence-platform-program-design.md` (SP0, sliced)
**Scope:** Backend (FastAPI/SQLAlchemy/PostGIS) + minimal frontend. The foundational data spine that gates SP1 (intelligence) and SP2 (operational).

## 1. Goal

Establish the canonical multi-tenant, multi-campaign spine the rest of the platform builds on:
- A **Campaign → Contest** container model, tenant-scoped, supporting **multiple concurrent contests** per campaign.
- A **territorial hierarchy** down to `seccion`/`casilla`, modeled with **redundant FKs on sección**, where the **base cartography is shared global reference** (ingested once; tenants add only their own custom areas).
- **App-layer scoping**: every campaign-scoped query auto-filtered by `(tenant_id, campaign_id)` through one chokepoint.
- **Alembic** introduced (replacing `create_all`) with a baseline + the SP0a migration.
- Minimal **admin API + frontend**: campaign/contest CRUD, catalogs, and a Topbar **campaign switcher** so the whole app operates within the active campaign.

This unblocks SP1 and SP2 in parallel.

## 2. Locked decisions (from brainstorming 2026-06-18)
1. **Slice:** this is SP0a (spine) only. SP0b (data integration + quality) and SP0c (RBAC-by-territory + legal/PII + notifications) follow as separate specs.
2. **Campaign ↔ Contest:** a Campaign groups **multiple concurrent Contests** (e.g., gubernatura + diputaciones + ayuntamientos). Operational data scopes to **campaign**; results/surveys/predictions reference a specific **contest**.
3. **Territory hierarchy:** redundant FK columns on `seccion` (estado/municipio/distrito_federal/distrito_local); fixed Mexican hierarchy.
4. **Isolation:** app-layer central filter (not Postgres RLS).
5. **Base territory:** **shared global reference** — base cartography has no tenant; tenant-specific areas (custom zones) are tenant-scoped.

## 3. Non-Goals (deferred)
- Data ingestion/quality engine (SP0b) — SP0a ships the territory **tables/columns**; bulk population is SP0b. SP0a may seed minimally for tests/dev.
- RBAC-by-territory enforcement, legal/PII/consent, notifications (SP0c).
- Any SP1/SP2 domain tables (results, census, CRM, structure) — only their **scoping foundations** exist here.
- Real-time, mobile, AI.

## 4. Current baseline (verified)
- Models: `Organization`, `User` (`UserRole`: superadmin/admin/analyst/viewer; org-bound, superadmin org-null), `ElectoralArea` (`UUIDMixin+TenantMixin+AuditMixin`, `AreaLevel`: country/region/state/municipality/district/precinct, generic `geometry`, `code`, `name`), `AuditLog`. Mixins in `app/models/base.py`: `UUIDMixin` (str UUID), `TenantMixin` (`organization_id` NOT NULL, CASCADE), `AuditMixin` (timestamps + soft-delete + actor).
- Auth: JWT + `get_tenant_context` (tenant from JWT, forced-password-change 428 gate).
- Schema bootstrap: `Base.metadata.create_all` in `app/bootstrap.py` (no migrations).
- Routers: auth, users, organizations, audit, analytics, intel, maps, sources, health.

## 5. Architecture

### 5.1 New models

**`app/models/catalog.py`**
- `Cargo` (catalog of contested offices): `{ id, key (e.g. "gubernatura","dip_federal","dip_local","presidencia_municipal","senaduria","presidencia"), label, ambito (federal|estatal|municipal), territory_level (AreaLevel the office maps to) }`. Global reference (no tenant).
- `Party`: `{ id, key, name, short, color }`. `Coalition`: `{ id, key, name, color }` + `CoalitionParty` link. Global reference (seedable; tenants don't fork the partisan catalog).

**`app/models/campaign.py`**
- `Campaign(UUIDMixin, TenantMixin, AuditMixin)`: `{ name, cycle (int year), status (Enum: draft|active|closed, default draft), license_tier (Enum, default standard), root_area_ids (assoc to ElectoralArea for the campaign's geographic scope) }`.
- `Contest(UUIDMixin, TenantMixin, AuditMixin)`: `{ campaign_id (FK campaigns, CASCADE), cargo_id (FK cargos), territory_id (FK electoral_areas — where the office is contested), election_date }`. A campaign has many contests.
- `CampaignMembership(UUIDMixin, AuditMixin)`: `{ user_id (FK users, CASCADE), campaign_id (FK campaigns, CASCADE), role (UserRole) }` — which campaigns a user may access (a user can be on several). Unique (user_id, campaign_id). Superadmin bypasses (sees all).

**`app/models/base.py` — add `CampaignMixin`**
- `campaign_id: Mapped[str]` (FK campaigns.id, CASCADE, indexed, NOT NULL). For SP1+/SP2+ campaign-scoped tables. NOT applied to territory/catalog (those are reference).

### 5.2 Territory hierarchy (modify `ElectoralArea`)
- **Extend `AreaLevel`** (keep existing values for back-compat; add): `distrito_federal`, `distrito_local`, `seccion`, `colonia`, `manzana`, `casilla`. (Existing `district`/`precinct` retained but new ingest uses the precise levels.)
- **Make `organization_id` nullable** on `ElectoralArea` (override TenantMixin for this model, or stop composing TenantMixin and declare a nullable `organization_id`): **NULL = shared global reference cartography**; non-null = a tenant's custom area. Add a partial/standard index on `organization_id`.
- **Add containment columns** (all nullable self-FKs to `electoral_areas.id`): `parent_id` (primary geographic container), and on `seccion` rows the redundant rollups `estado_id`, `municipio_id`, `distrito_federal_id`, `distrito_local_id`; `casilla` rows carry `seccion_id`. A `self` relationship exposes `parent`/`children`.
- **Migrate existing data:** the currently-seeded base cartography (32 estados + ~1854 municipios under org `atlas`) → set `organization_id = NULL` (promote to global reference). Document the one-time data migration in the Alembic revision.

### 5.3 Scoping enforcement (app layer)
- Extend the request context: in addition to tenant (from JWT), resolve the **active campaign** from an `X-Campaign-Id` request header. Validate it against the caller's `CampaignMembership` (superadmin: any). Expose `ctx.campaign_id`.
- New `app/core/scoping.py`: `scoped_query(session, model, ctx)` returns a `select(model)` pre-filtered by `organization_id == ctx.tenant_id` and, if the model has `campaign_id`, `campaign_id == ctx.campaign_id`; soft-delete (`deleted_at IS NULL`) applied as today. All campaign-scoped reads/writes go through it. Territory/catalog reads use a reference-aware filter (`organization_id IS NULL OR == tenant`).
- `get_tenant_context` extended → `get_campaign_context` (or augment the existing dependency) so routers receive `(tenant_id, campaign_id, user, role)`. Endpoints that are campaign-agnostic (catalogs, global territory, admin of campaigns themselves) opt out.

### 5.4 Alembic
- Add Alembic (`alembic`, `alembic.ini`, `migrations/`). Configure `env.py` to import `Base.metadata` + the DB URL from settings.
- **Revision 1 (baseline):** the current schema as-is (organizations, users, electoral_areas[old shape], audit_logs) so existing prod DB stamps cleanly.
- **Revision 2 (SP0a):** add cargos/parties/coalitions/campaigns/contests/campaign_memberships; add territory columns + nullable organization_id + new AreaLevel enum values; data-migrate base cartography to global (`organization_id = NULL`).
- `app/bootstrap.py`: switch from `create_all` to `alembic upgrade head` at startup (keep create_all only for the SQLite test path if simpler, gated by dialect). Document the Railway startup implication (migrations run in the FastAPI lifespan, same place bootstrap runs today — private networking available there, unlike the release phase).

### 5.5 API surface (new routers)
- `routers/campaigns.py`: CRUD campaigns (admin+), CRUD contests, list "my campaigns" (from membership), set/get active campaign. Tenant-scoped; admin-gated for writes.
- `routers/catalogs.py`: read cargos/parties/coalitions; seed endpoint (superadmin) or seed script.
- Territory: extend `routers/maps.py` (or new `routers/territory.py`) to serve the hierarchy (children of an area, ancestors of a sección) reading global+tenant reference. (Deep cartography population is SP0b.)

### 5.6 Frontend (minimal)
- **Campaign switcher** in `Topbar` (next to the theme toggle): a dropdown of the user's campaigns; selection stored in a `campaignStore` (zustand, like `themeStore`) + sent as `X-Campaign-Id` on every API call (axios interceptor). The whole app operates within the active campaign.
- **Admin screens** under Administración: Campaigns list/create/edit (+ contests per campaign), reusing `DataTable`/`PageHeader`/`Modal`/the design system. Catalog views read-only.
- No theming/UX rework — consumes the existing design system.

## 6. Data flow
1. User logs in → JWT (tenant + role) as today.
2. Frontend loads "my campaigns" → user picks one → `campaignStore` holds it → axios sends `X-Campaign-Id`.
3. Backend dependency resolves `(tenant_id, campaign_id)` (validates membership) → routers use `scoped_query` → all campaign data is isolated.
4. Territory + catalogs resolve as shared reference (global) unioned with the tenant's custom areas.
5. Results/surveys (future SPs) attach to a `contest_id`; operational data (future) attaches `campaign_id` via `CampaignMixin`.

## 7. Error handling & edge cases
- **Missing/invalid `X-Campaign-Id`:** campaign-scoped endpoints return 400 (missing) / 403 (not a member). Campaign-agnostic endpoints ignore it.
- **Superadmin:** bypasses membership (may act across tenants/campaigns); still must pass a campaign id for campaign-scoped reads (or an explicit "all" mode — keep simple: superadmin must select a campaign too).
- **Territory nullable tenant:** queries must use `organization_id IS NULL OR = tenant` for reference areas; never leak one tenant's custom areas to another.
- **Existing data migration:** if base cartography isn't cleanly identifiable as "the atlas seed," the migration must be explicit about which rows go global (by org id `atlas` + level in {state,municipality}). Verify counts before/after.
- **SQLite tests:** geometry already degrades to Text; ensure new enum values + nullable FK + self-FK work on SQLite; Alembic must run (or tests keep `create_all` on SQLite).
- **Cascade safety:** deleting a campaign cascades contests + memberships (not territory/catalog).
- **Backward compatibility:** existing routers (maps/analytics/audit) keep working pre-switcher by treating campaign as optional until they're migrated; SP0a doesn't break the current app.

## 8. Testing & verification
- **Backend:** pytest (conftest builds SQLite schema) — new tests: campaign/contest CRUD, membership-gated access (member vs non-member vs superadmin), `scoped_query` isolation (tenant A cannot read tenant B / campaign 1 cannot read campaign 2), territory reference resolution (global + tenant union), Alembic upgrade/downgrade on a scratch DB. Target: isolation tests are mandatory (the #1 program risk).
- **Migrations:** `alembic upgrade head` then `downgrade` on a throwaway Postgres; verify the base-cartography data migration counts.
- **Frontend:** `npm run lint` + `npm run build`; manual — campaign switcher changes context, admin CRUD works, app still renders within a campaign.
- **Manual API:** with two seeded tenants/campaigns, confirm cross-campaign reads return empty/403.

## 9. Rollout / sequencing (within SP0a)
1. Alembic baseline (stamp current schema) — no behavior change.
2. Catalogs + Campaign/Contest/Membership models + migration.
3. `CampaignMixin` + `scoping.py` + campaign context dependency.
4. Territory hierarchy columns + nullable tenant + AreaLevel + data migration.
5. Campaigns/catalogs/territory routers.
6. Frontend campaignStore + switcher + admin screens.
7. Tests (isolation-focused) + full build gate.
Each step: branch `feat/sp0a-*`, subagent-driven, reviewed, build/pytest gated. Deploy via main→Railway when SP0a is green.

## 10. Open questions (resolve in plan, not blocking)
- Exact `license_tier` values (placeholder enum now; the tier→feature matrix is a later concern).
- Whether `get_tenant_context` is extended in place vs a new `get_campaign_context` dependency (mechanical; decide in plan).
- Seed strategy for cargos/parties (script vs endpoint) — pick script to match existing `scripts/` patterns.
