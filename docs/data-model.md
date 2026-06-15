# Data Model — Ágora Civic Intelligence

All identifiers are **string UUIDs**. All timestamps are timezone-aware
(`TIMESTAMPTZ`). Business entities are tenant-scoped via `organization_id`.

## Atlas canon mixins (`app/models/base.py`)

Composed onto entities to enforce platform invariants at the schema level:

- **`UUIDMixin`** — `id: str` PK, default `str(uuid4())`.
- **`TenantMixin`** — `organization_id: str` FK → `organizations.id`, indexed,
  not-null. Used on business entities. Tenant context is derived from the JWT.
- **`AuditMixin`** — `created_at`, `updated_at` (server default now / onupdate),
  `deleted_at` (nullable; soft delete), `created_by`, `updated_by` (user id).

| Entity          | UUID | Tenant | Audit | Notes                                  |
|-----------------|:----:|:------:|:-----:|----------------------------------------|
| `organizations` |  ✅  |   —    |  ✅   | The tenant root.                       |
| `users`         |  ✅  |  ~*    |  ✅   | `organization_id` nullable for superadmin. |
| `electoral_areas`| ✅  |   ✅   |  ✅   | PostGIS geometry.                      |
| `audit_logs`    |  ✅  |   —    |   —   | Append-only; own `created_at`.         |

\* Users carry `organization_id` but it is nullable so platform-level
superadmins exist without a single tenant.

## organizations
`id`, `name`, `slug` (unique, indexed), `is_active`, + audit columns.

## users
`id`, `organization_id` (FK, nullable, indexed), `email` (unique, indexed),
`full_name`, `hashed_password` (bcrypt), `role` (enum: `superadmin` / `admin` /
`analyst` / `viewer`), `is_active`, + audit columns.

## electoral_areas
`id`, `organization_id` (FK, not-null), `name`, `code` (indexed, nullable),
`level` (enum: country / region / state / municipality / district / precinct),
`geometry` (`geoalchemy2.Geometry(geometry_type="GEOMETRY", srid=4326)` —
points / polygons / multipolygons; degrades to text on non-PostGIS engines for
test portability), + audit columns.

## audit_logs (append-only)
`id`, `actor_id` (indexed), `organization_id` (indexed), `action` (indexed,
e.g. `auth.login`), `entity_type`, `entity_id`, `metadata` (JSONB; generic JSON
off-Postgres — mapped to the `meta` attribute to avoid the SQLAlchemy
`metadata` clash), `created_at` (indexed). No update or delete paths.

## Relationships
- `organizations 1—N users`
- `organizations 1—N electoral_areas`
- `audit_logs` reference organization + actor by id (denormalized, append-only).

## Conventions
- PostGIS required: `CREATE EXTENSION IF NOT EXISTS postgis;` (handled by
  `scripts/railway_init.py`).
- Geometry exchanged at the API boundary as GeoJSON (SRID 4326).
- Soft delete: queries filter `deleted_at IS NULL`.
