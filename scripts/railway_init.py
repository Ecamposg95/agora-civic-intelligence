#!/usr/bin/env python
"""Idempotent bootstrap for Railway deploys.

Safe to run on every deploy (Procfile ``release`` phase):
  1. Enable the PostGIS extension (PostgreSQL only).
  2. Create tables (or rely on Alembic migrations).
  3. Seed a base organization and a super-admin user if absent.

Seed credentials come from env (never hardcoded):
  SEED_ORG_NAME, SEED_ORG_SLUG, SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD
"""

import os
import sys

# Allow running as `python scripts/railway_init.py` from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select, text  # noqa: E402

import app.models  # noqa: E402,F401  (register models on Base.metadata)
from app.core.security import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


def _enable_postgis() -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    print("✓ PostGIS extension ensured")


def _create_tables() -> None:
    Base.metadata.create_all(engine)
    print("✓ Tables ensured")


def _seed() -> None:
    org_name = os.getenv("SEED_ORG_NAME", "Atlas Tech")
    org_slug = os.getenv("SEED_ORG_SLUG", "atlas")
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@atlas.gov")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD")

    with SessionLocal() as db:
        org = db.execute(
            select(Organization).where(Organization.slug == org_slug)
        ).scalar_one_or_none()
        if org is None:
            org = Organization(name=org_name, slug=org_slug)
            db.add(org)
            db.flush()
            print(f"✓ Seeded organization '{org_slug}'")

        existing = db.execute(
            select(User).where(User.email == admin_email)
        ).scalar_one_or_none()
        if existing is None:
            if not admin_password:
                print(
                    "! SEED_ADMIN_PASSWORD not set — skipping super-admin seed. "
                    "Set it to create the initial admin."
                )
            else:
                db.add(
                    User(
                        email=admin_email,
                        full_name="Super Admin",
                        hashed_password=hash_password(admin_password),
                        role=UserRole.SUPERADMIN,
                        organization_id=org.id,
                    )
                )
                print(f"✓ Seeded super-admin '{admin_email}'")
        db.commit()


def main() -> None:
    _enable_postgis()
    _create_tables()
    _seed()
    print("✓ railway_init complete")


if __name__ == "__main__":
    main()
