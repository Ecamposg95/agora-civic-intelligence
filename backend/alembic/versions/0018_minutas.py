"""0018 minutas & acuerdos — meeting minutes and action items

Revision ID: 0018_minutas
Revises: 0017_operacion
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_minutas"
down_revision = "0017_operacion"
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
    if not _table_exists("minutas"):
        op.create_table(
            "minutas",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("titulo", sa.String(255), nullable=False),
            sa.Column("fecha", sa.Date(), nullable=False),
            sa.Column("lugar", sa.String(255), nullable=True),
            sa.Column("tipo", sa.String(20), nullable=False, server_default="REUNION"),
            sa.Column("asistentes", sa.JSON(), nullable=False),
            sa.Column("cuerpo", sa.Text(), nullable=True),
            sa.Column("estado", sa.String(20), nullable=False, server_default="BORRADOR"),
            sa.Column("area_id", sa.String(36), sa.ForeignKey("electoral_areas.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )
    if not _index_exists("minutas", "ix_minutas_campaign_fecha"):
        op.create_index("ix_minutas_campaign_fecha", "minutas", ["campaign_id", "fecha"])
    if not _index_exists("minutas", "ix_minutas_campaign_estado"):
        op.create_index("ix_minutas_campaign_estado", "minutas", ["campaign_id", "estado"])

    if not _table_exists("acuerdos"):
        op.create_table(
            "acuerdos",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("minuta_id", sa.String(36), sa.ForeignKey("minutas.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("texto", sa.String(2000), nullable=False),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("responsable_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("fecha_limite", sa.Date(), nullable=True),
            sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
            sa.Column("work_item_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )
    if not _index_exists("acuerdos", "ix_acuerdos_campaign_responsable_estado"):
        op.create_index("ix_acuerdos_campaign_responsable_estado", "acuerdos", ["campaign_id", "responsable_id", "estado"])


def downgrade() -> None:
    if _table_exists("acuerdos"):
        op.drop_table("acuerdos")
    if _table_exists("minutas"):
        op.drop_table("minutas")
