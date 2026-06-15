# Deployment — Railway

Ágora is **Railway-first** and deploys as a **single application service** (the
FastAPI backend serves both the `/api/*` JSON API and the built React SPA) plus
a **PostgreSQL/PostGIS** database service. Build is **Nixpacks** (no Dockerfile).

## Services

### 1. App (backend + SPA)
- **Root directory:** repo root.
- **Builder:** Nixpacks, driven by `nixpacks.toml`:
  - installs Node 20 + Python 3.12,
  - `pip install -r backend/requirements.txt`,
  - `cd frontend && npm ci && npm run build` (produces `frontend/dist`).
- **Start (Procfile):**
  ```
  web: uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
  ```
- **Release (Procfile)** — idempotent bootstrap, safe on every deploy:
  ```
  release: python scripts/railway_init.py
  ```
- **Health check path:** `/api/health`
- The backend locates the SPA via `FRONTEND_DIST` (default `../frontend/dist`),
  with fallbacks resolved relative to the repo root and CWD, then serves
  `index.html` for any non-`/api` path so React Router deep-links work.

#### App variables
```
DATABASE_URL=postgresql://...        # from the Postgres service (driver auto-normalized)
SECRET_KEY=<strong-random-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ENVIRONMENT=production
CORS_ORIGINS=https://<your-app-domain>
FRONTEND_DIST=../frontend/dist
# Seed (release step) — set a password to create the first super-admin:
SEED_ORG_NAME=Atlas Tech
SEED_ORG_SLUG=atlas
SEED_ADMIN_EMAIL=admin@atlas.gov
SEED_ADMIN_PASSWORD=<strong-secret>
```
> `config.py` normalizes `postgres://` / `postgresql://` → `postgresql+psycopg://`,
> so you can paste Railway's reference variable directly.

> Frontend build: `VITE_API_URL` defaults to `/api`. Because the backend serves
> the SPA at the same origin, you normally do **not** need to set it.

### 2. Database (PostgreSQL + PostGIS)
- Provision PostgreSQL using the **`postgis/postgis`** image so PostGIS is
  available out of the box.
- `scripts/railway_init.py` runs `CREATE EXTENSION IF NOT EXISTS postgis`
  automatically during the release phase.
- Reference the DB connection string into the App service as `DATABASE_URL`.

## `scripts/railway_init.py`
Idempotent and safe to re-run every deploy:
1. Enables PostGIS (PostgreSQL only).
2. Creates tables (`Base.metadata.create_all`) — or use Alembic migrations.
3. Seeds the base organization + a super-admin **only if absent** (the admin is
   created only when `SEED_ADMIN_PASSWORD` is set — never a hardcoded default).

## Migrations (Alembic)
Alembic is wired to the app settings and ORM metadata. For an explicit
migration workflow instead of `create_all`:
```bash
cd backend
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## Post-deploy checklist
- [ ] Database provisioned from `postgis/postgis`; PostGIS extension enabled.
- [ ] App `release` step (`railway_init.py`) ran without error.
- [ ] App `/api/health` returns `200`.
- [ ] Visiting the app domain serves the SPA; deep links (e.g. `/maps`) resolve.
- [ ] `CORS_ORIGINS` includes the app domain (only needed for cross-origin calls).
- [ ] `SECRET_KEY` and `SEED_ADMIN_PASSWORD` are strong, unique secrets.
