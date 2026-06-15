# Architecture — Ágora Civic Intelligence

## Overview

Ágora is an **API-first** GovTech platform. The backend owns all security,
authorization, validation and business rules; the frontend consumes `/api/*`.
In production a **single Railway service** runs FastAPI, which serves both the
JSON API and the built React SPA.

```
                         Railway App service (single)
┌───────────────────────────────────────────────────────────────┐
│  FastAPI                                                         │
│   ├─ /api/*        Routers → Services → Models (SQLAlchemy 2.0)  │
│   ├─ /api/docs     OpenAPI / Swagger / ReDoc                     │
│   └─ /* (SPA)      StaticFiles + catch-all → index.html          │
└───────────────────────────────┬───────────────────────────────┘
                                 │
                      ┌──────────▼───────────┐
                      │ PostgreSQL + PostGIS  │  (postgis/postgis image)
                      └──────────────────────┘

Dev: Vite (5173) ──proxy /api──▶ FastAPI (8000)
```

## Backend layering

| Layer        | Responsibility                                             |
|--------------|------------------------------------------------------------|
| `routers/`   | HTTP surface, status codes, response shapes                |
| `services/`  | Business logic, orchestration, audit writes                |
| `models/`    | SQLAlchemy 2.0 ORM + Atlas canon mixins                     |
| `schemas/`   | Pydantic v2 validation & serialization at the boundary     |
| `core/`      | Config (env), security primitives, logging                 |
| `dependencies`| Auth, tenant context, RBAC guards                         |
| `utils/`     | Cross-cutting helpers (pagination)                         |

Dependencies flow inward: routers → services → models. Models never import
routers.

## Multi-tenancy & the Golden Rules

Enforced in generated code:

1. Every query on a business entity filters by `organization_id`.
2. `organization_id` on writes comes from the JWT tenant context, never input.
3. Endpoints never return raw ORM objects — always a Pydantic schema.
4. RBAC is enforced in the API layer via dependencies (`require_roles`).
5. Sensitive operations emit an `audit_log` row.
6. No hardcoded secrets — all config from env.
7. Paginated lists return `{ items, total, limit, offset }`.
8. Errors use the envelope `{ "error": { "message", "status" } }`.

`dependencies.py` derives `TenantContext` (user + `organization_id` + role) from
the authenticated user (sourced from the JWT). Superadmins may operate across
tenants; everyone else is confined to their organization.

## Atlas canon mixins

`models/base.py` defines `UUIDMixin` (string UUID PK), `TenantMixin`
(`organization_id` FK) and `AuditMixin` (timestamps + soft delete +
`created_by`/`updated_by`). Every entity composes the relevant mixins — see
[`data-model.md`](data-model.md).

## Backend serves the SPA

`main.py` mounts `/assets` from the built `frontend/dist` and registers a
catch-all GET that returns `index.html` for any non-`/api` path, so client-side
routing survives refreshes and deep links. `/api/docs`, `/api/redoc` and
`/api/openapi.json` remain available. The dist location is resolved from
`FRONTEND_DIST` with sensible fallbacks.

## Geospatial

`ElectoralArea.geometry` is a PostGIS `GEOMETRY(SRID 4326)` via GeoAlchemy2
(points / polygons / multipolygons). `GET /api/maps/areas` emits a GeoJSON
`FeatureCollection` (via `ST_AsGeoJSON` on PostGIS). The frontend renders it on
a **MapLibre GL** basemap (OpenStreetMap raster — no API-key lock-in).

## Frontend

Vite + React + TypeScript, **Tailwind CSS** (dark-first command-center theme),
React Router v6, Zustand (auth store, token persisted), Axios (bearer
interceptor + 401 handling), **Recharts** for dashboards, **MapLibre GL** for
maps. Structure: `api/`, `store/`, `pages/`, `components/{ui,layout,maps,dashboards}`,
`types/`.

## Future modules

Maps, executive dashboards, electoral data governance, participation analytics
and the Institutional AI Analyst all attach to the same API spine and tenant
model.
