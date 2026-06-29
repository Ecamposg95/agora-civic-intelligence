"""SPA-3: widen registros unique constraint to (campaign_id, activista_id, client_uuid).

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-29

Notes
-----
* down_revision is 0008. SP0b-2b (0007) is still on an unmerged branch; when it
  merges, a separate Alembic merge-migration (two down_revisions) is needed.
* Widening a UNIQUE constraint = drop old + create new. PostgreSQL supports
  ALTER TABLE DROP/ADD CONSTRAINT directly. SQLite does not, so it is handled via
  batch_alter_table (table rebuild). Both paths are guarded for idempotency.
* The model (Registro.__table_args__) is the source of truth for SQLite test DBs
  built with create_all; this migration keeps prod PG in sync.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

OLD = "uq_registros_campaign_client_uuid"
NEW = "uq_registros_campaign_activista_client_uuid"
COLS = ["campaign_id", "activista_id", "client_uuid"]


def _uniques(table: str) -> set[str]:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table):
        return set()
    return {uc["name"] for uc in sa.inspect(bind).get_unique_constraints(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("registros"):
        return
    is_pg = bind.dialect.name == "postgresql"
    existing = _uniques("registros")

    if is_pg:
        if OLD in existing:
            op.drop_constraint(OLD, "registros", type_="unique")
        if NEW not in existing:
            op.create_unique_constraint(NEW, "registros", COLS)
    else:
        # SQLite: rebuild the table. Drop old + add new inside one batch op.
        with op.batch_alter_table("registros", schema=None) as batch:
            if OLD in existing:
                batch.drop_constraint(OLD, type_="unique")
            if NEW not in existing:
                batch.create_unique_constraint(NEW, COLS)


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("registros"):
        return
    is_pg = bind.dialect.name == "postgresql"
    existing = _uniques("registros")

    if is_pg:
        if NEW in existing:
            op.drop_constraint(NEW, "registros", type_="unique")
        if OLD not in existing:
            op.create_unique_constraint(OLD, "registros", ["campaign_id", "client_uuid"])
    else:
        with op.batch_alter_table("registros", schema=None) as batch:
            if NEW in existing:
                batch.drop_constraint(NEW, type_="unique")
            if OLD not in existing:
                batch.create_unique_constraint(OLD, ["campaign_id", "client_uuid"])
