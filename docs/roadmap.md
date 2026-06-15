# Roadmap — Ágora Civic Intelligence

## Phase 0 — Foundation (this scaffold) ✅
- Monorepo structure (backend / frontend / docs).
- FastAPI app: health, auth login, users, organizations, maps, analytics.
- SQLAlchemy 2.0 models + Alembic, PostGIS geometry.
- Pydantic v2 schemas, production-safe CORS, error envelope, audit-ready model.
- Vite + React + TS command center UI (login, dashboard, maps, analytics).
- Railway deployment configuration.

## Phase 1 — Authentication & tenancy
- Real login flow, refresh tokens, password reset.
- Organization onboarding & user invitations.
- Role-based authorization enforced per endpoint.
- Audit logging middleware on sensitive actions.

## Phase 2 — Geospatial core
- PostGIS-backed electoral area CRUD + GeoJSON endpoints.
- Vector tiles / GeoJSON serving for the map explorer.
- MapLibre basemap + layer rendering and styling.
- Import pipelines (Shapefile / GeoJSON ingestion).

## Phase 3 — Analytics & dashboards
- Real participation metrics and aggregation pipelines.
- Configurable executive dashboards and exports.
- Time-series and territorial comparisons.

## Phase 4 — Institutional AI analyst
- Natural-language querying over governed data.
- Cited, traceable briefings with audit logging.
- Guardrails: privacy, aggregation-only, tenant isolation.

## Phase 5 — Governance & scale
- Fine-grained permissions and data classification.
- Multi-institution operations and SLAs.
- Observability, backups, and compliance reporting.
