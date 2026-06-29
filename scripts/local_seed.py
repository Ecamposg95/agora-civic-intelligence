#!/usr/bin/env python
"""Seed a local SQLite database with demo users for the UI walkthrough.

Run with DATABASE_URL pointing at a SQLite file (see local run instructions).
Creates the PostGIS-free tables (organizations, users, audit_logs) and a set of
demo accounts whose passwords are pre-set (no forced change), so you can log in
and explore the UI immediately.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo12345")

DEMO_USERS = [
    ("admin@agora.gob.mx", "Admin Demo", UserRole.ADMIN),
    ("ana.analista@agora.gob.mx", "Ana Analista", UserRole.ANALYST),
    ("victor.viewer@agora.gob.mx", "Víctor Viewer", UserRole.VIEWER),
    ("sofia.admin@agora.gob.mx", "Sofía Admin", UserRole.ADMIN),
]

# Activist leadership profiles seeded with their own (non-default) password.
# (email, full_name, role, password)
LEADERSHIP_USERS = [
    ("lucy@atlastech.mx", "Lucy — Dirigente de Activismo", UserRole.LIDER, "78451289"),
]


def main() -> None:
    # Only the SQLite-safe tables (electoral_areas uses PostGIS geometry).
    Base.metadata.create_all(
        engine,
        tables=[Organization.__table__, User.__table__, AuditLog.__table__],
    )
    with SessionLocal() as db:
        org = db.execute(
            select(Organization).where(Organization.slug == "atlas")
        ).scalar_one_or_none()
        if org is None:
            org = Organization(name="Atlas Tech", slug="atlas")
            db.add(org)
            db.flush()

        for email, name, role in DEMO_USERS:
            exists = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if exists is None:
                db.add(
                    User(
                        email=email,
                        full_name=name,
                        role=role,
                        organization_id=org.id,
                        hashed_password=hash_password(DEMO_PASSWORD),
                        must_change_password=False,
                        is_active=True,
                    )
                )

        for email, name, role, password in LEADERSHIP_USERS:
            exists = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if exists is None:
                db.add(
                    User(
                        email=email,
                        full_name=name,
                        role=role,
                        organization_id=org.id,
                        hashed_password=hash_password(password),
                        must_change_password=False,
                        is_active=True,
                    )
                )
        db.commit()

    print("✓ Seed complete")
    print(f"  Login: admin@agora.gob.mx / {DEMO_PASSWORD}  (rol admin)")
    print("  Login: lucy@atlastech.mx / 78451289  (rol lider — dirigente de activismo)")


if __name__ == "__main__":
    main()
