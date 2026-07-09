"""0019 scrum — sprints, work_items, work_item_tasks

Revision ID: 0019_scrum
Revises: 0018_minutas
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_scrum"
down_revision = "0018_minutas"
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _table_exists(name: str) -> bool:
    return name in _insp().get_table_names()


def _index_exists(table: str, name: str) -> bool:
    if not _table_exists(table):
        return False
    return any(ix["name"] == name for ix in _insp().get_indexes(table))


def upgrade() -> None:
    if not _table_exists("sprints"):
        op.create_table(
            "sprints",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("nombre", sa.String(120), nullable=False),
            sa.Column("objetivo", sa.String(500), nullable=True),
            sa.Column("fecha_inicio", sa.Date(), nullable=False),
            sa.Column("fecha_fin", sa.Date(), nullable=False),
            sa.Column("estado", sa.String(20), nullable=False, server_default="PLANIFICACION"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )
    if not _index_exists("sprints", "ix_sprints_campaign_estado"):
        op.create_index("ix_sprints_campaign_estado", "sprints", ["campaign_id", "estado"])

    if not _table_exists("work_items"):
        op.create_table(
            "work_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("titulo", sa.String(255), nullable=False),
            sa.Column("descripcion", sa.String(2000), nullable=True),
            sa.Column("tipo", sa.String(20), nullable=False, server_default="HISTORIA"),
            sa.Column("story_points", sa.Integer(), nullable=True),
            sa.Column("estado", sa.String(20), nullable=False, server_default="POR_HACER"),
            sa.Column("prioridad", sa.String(10), nullable=False, server_default="MEDIA"),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sprint_id", sa.String(36), sa.ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True),
            sa.Column("responsable_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("origin_acuerdo_id", sa.String(36), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )
    for ix, cols in [
        ("ix_work_items_campaign_sprint_estado", ["campaign_id", "sprint_id", "estado"]),
        ("ix_work_items_campaign_estado", ["campaign_id", "estado"]),
        ("ix_work_items_campaign_responsable", ["campaign_id", "responsable_id"]),
    ]:
        if not _index_exists("work_items", ix):
            op.create_index(ix, "work_items", cols)

    if not _table_exists("work_item_tasks"):
        op.create_table(
            "work_item_tasks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("work_item_id", sa.String(36), sa.ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("texto", sa.String(500), nullable=False),
            sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("responsable_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )


def downgrade() -> None:
    for t in ("work_item_tasks", "work_items", "sprints"):
        if _table_exists(t):
            op.drop_table(t)
