"""0020 minuta.sprint_id — link ceremony minutas to a sprint

Revision ID: 0020_minuta_sprint
Revises: 0019_scrum
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_minuta_sprint"
down_revision = "0019_scrum"
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _column_exists(table: str, col: str) -> bool:
    return any(c["name"] == col for c in _insp().get_columns(table))


def _index_exists(table: str, name: str) -> bool:
    return any(ix["name"] == name for ix in _insp().get_indexes(table))


def upgrade() -> None:
    if not _column_exists("minutas", "sprint_id"):
        with op.batch_alter_table("minutas") as batch:
            batch.add_column(sa.Column("sprint_id", sa.String(36), nullable=True))
    if not _index_exists("minutas", "ix_minutas_sprint_id"):
        op.create_index("ix_minutas_sprint_id", "minutas", ["sprint_id"])


def downgrade() -> None:
    if _index_exists("minutas", "ix_minutas_sprint_id"):
        op.drop_index("ix_minutas_sprint_id", table_name="minutas")
    if _column_exists("minutas", "sprint_id"):
        with op.batch_alter_table("minutas") as batch:
            batch.drop_column("sprint_id")
