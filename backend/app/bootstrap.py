"""Idempotent database bootstrap.

Runs at application startup (FastAPI lifespan) and is also callable from
``scripts/railway_init.py`` for local/manual use.

On Railway the bootstrap MUST run at runtime (not in the Nixpacks ``release``
phase): private networking — and therefore ``*.railway.internal`` DNS — is only
available once the service is running, so a release-phase connection to the
database fails with "Name or service not known".

Steps (all idempotent, safe to run on every boot):
  1. Wait for the database to accept connections (handles cold-start races).
  2. Enable the PostGIS extension (PostgreSQL only) — required before the
     ``electoral_areas`` table with its ``Geometry`` column can be created.
  3. Create tables.
  4. Seed a base organization and a super-admin user if absent.

Seed credentials come from env (never hardcoded):
  SEED_ORG_NAME, SEED_ORG_SLUG, SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD
"""

import os
import time

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

import app.models  # noqa: F401  (register models on Base.metadata)
from app.core.logging import get_logger
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.organization import Organization
from app.models.user import User, UserRole

logger = get_logger("agora.bootstrap")


def _wait_for_db(max_attempts: int = 20, delay_seconds: float = 3.0) -> None:
    """Block until the database accepts a connection, or give up after retries."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            logger.warning(
                "Database not ready (attempt %s/%s): %s",
                attempt,
                max_attempts,
                exc,
            )
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds)


def _enable_postgis() -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    logger.info("PostGIS extension ensured")


def _create_tables() -> None:
    Base.metadata.create_all(engine)
    logger.info("Tables ensured")


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
            logger.info("Seeded organization '%s'", org_slug)

        existing = db.execute(
            select(User).where(User.email == admin_email)
        ).scalar_one_or_none()
        if existing is None:
            if not admin_password:
                logger.warning(
                    "SEED_ADMIN_PASSWORD not set — skipping super-admin seed. "
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
                logger.info("Seeded super-admin '%s'", admin_email)
        db.commit()


def run_bootstrap() -> None:
    """Run the full idempotent bootstrap sequence."""
    _wait_for_db()
    _enable_postgis()
    _create_tables()
    _seed()
    logger.info("Database bootstrap complete")
