"""SPA-4: privacy_notices + privacy_acceptances tables (aviso versionado).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-29

Notes
-----
* down_revision is 0009 — the current head on the integrated SPA-1+2+3 branch
  (feat/spa4-compliance). When SP0b-2b (0007) and any pending branches merge,
  a separate Alembic merge-migration (multiple down_revisions) is needed.
* NO enum types — PrivacyNotice/PrivacyAcceptance use only Boolean/Text/String,
  so no autocommit_block is required.
* Idempotent: _table_exists + _index_exists guards on every DDL statement.
* organization_id is NULLABLE (NULL = global platform aviso). PostgreSQL treats
  two NULLs as unequal in unique constraints; application logic (seed + service
  layer) enforces "one active global v1" invariant.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def _index_exists(table: str, index: str) -> bool:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table):
        return False
    return any(ix["name"] == index for ix in sa.inspect(bind).get_indexes(table))


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. privacy_notices                                                   #
    # ------------------------------------------------------------------ #
    if not _table_exists("privacy_notices"):
        op.create_table(
            "privacy_notices",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id",
                sa.String(length=36),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("version", sa.String(length=40), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "organization_id", "version",
                name="uq_privacy_notices_org_version",
            ),
        )

    if not _index_exists("privacy_notices", "ix_privacy_notices_organization_id"):
        op.create_index(
            "ix_privacy_notices_organization_id", "privacy_notices", ["organization_id"]
        )
    if not _index_exists("privacy_notices", "ix_privacy_notices_org_active"):
        op.create_index(
            "ix_privacy_notices_org_active",
            "privacy_notices",
            ["organization_id", "is_active"],
        )

    # ------------------------------------------------------------------ #
    # 2. privacy_acceptances                                               #
    # ------------------------------------------------------------------ #
    if not _table_exists("privacy_acceptances"):
        op.create_table(
            "privacy_acceptances",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "registro_id",
                sa.String(length=36),
                sa.ForeignKey("registros.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "notice_id",
                sa.String(length=36),
                sa.ForeignKey("privacy_notices.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("aviso_version", sa.String(length=40), nullable=False),
            sa.Column(
                "accepted_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _index_exists("privacy_acceptances", "ix_privacy_acceptances_registro_id"):
        op.create_index(
            "ix_privacy_acceptances_registro_id",
            "privacy_acceptances",
            ["registro_id"],
        )
    if not _index_exists("privacy_acceptances", "ix_privacy_acceptances_notice_id"):
        op.create_index(
            "ix_privacy_acceptances_notice_id",
            "privacy_acceptances",
            ["notice_id"],
        )


def downgrade() -> None:
    if _table_exists("privacy_acceptances"):
        op.drop_table("privacy_acceptances")

    if _index_exists("privacy_notices", "ix_privacy_notices_org_active"):
        op.drop_index("ix_privacy_notices_org_active", table_name="privacy_notices")
    if _index_exists("privacy_notices", "ix_privacy_notices_organization_id"):
        op.drop_index(
            "ix_privacy_notices_organization_id", table_name="privacy_notices"
        )
    if _table_exists("privacy_notices"):
        op.drop_table("privacy_notices")
