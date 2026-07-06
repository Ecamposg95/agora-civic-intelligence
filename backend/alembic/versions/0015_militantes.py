"""0015 militantes + campaigns.meta_afiliacion

Revision ID: 0015_militantes
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_militantes"
down_revision = "0014"
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


def _column_exists(table: str, col: str) -> bool:
    if not _table_exists(table):
        return False
    return any(c["name"] == col for c in _insp().get_columns(table))


def upgrade() -> None:
    if not _table_exists("militantes"):
        op.create_table(
            "militantes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("activista_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("nombre_completo", sa.String(255), nullable=False),
            sa.Column("sexo", sa.String(1), nullable=True),
            sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
            sa.Column("seccion", sa.String(20), nullable=True),
            sa.Column("email", sa.String(160), nullable=True),
            sa.Column("telefono", sa.String(40), nullable=True),
            sa.Column("calle_numero", sa.String(500), nullable=True),
            sa.Column("colonia", sa.String(255), nullable=True),
            sa.Column("cp", sa.String(10), nullable=True),
            sa.Column("municipio", sa.String(120), nullable=True),
            sa.Column("estado_domicilio", sa.String(120), nullable=True),
            sa.Column("es_activista", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("estructura", sa.String(120), nullable=True),
            sa.Column("promotor", sa.String(160), nullable=True),
            sa.Column("folio", sa.String(40), nullable=False),
            sa.Column("folio_externo", sa.String(60), nullable=True),
            sa.Column("fecha_afiliacion", sa.Date(), nullable=True),
            sa.Column("curp_enc", sa.LargeBinary(), nullable=True),
            sa.Column("curp_masked", sa.String(20), nullable=True),
            sa.Column("clave_elector_enc", sa.LargeBinary(), nullable=True),
            sa.Column("clave_masked", sa.String(20), nullable=True),
            sa.Column("credencial_frente_key", sa.String(300), nullable=True),
            sa.Column("credencial_reverso_key", sa.String(300), nullable=True),
            sa.Column("firma_key", sa.String(300), nullable=True),
            sa.Column("estado", sa.String(20), nullable=False, server_default="REGISTRADO"),
            sa.Column("validado_por", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("validado_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("observacion_validacion", sa.String(500), nullable=True),
            sa.Column("quality_flags", sa.JSON(), nullable=True),
            sa.Column("consentimiento", sa.Boolean(), nullable=False),
            sa.Column("consentimiento_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("aviso_version", sa.String(40), nullable=True),
            sa.Column("manifestacion_voluntad", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("client_uuid", sa.String(64), nullable=True),
            sa.Column("lat", sa.Float(), nullable=True),
            sa.Column("lng", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("updated_by", sa.String(36), nullable=True),
        )
    if not _index_exists("militantes", "ix_militantes_campaign_activista"):
        op.create_index("ix_militantes_campaign_activista", "militantes", ["campaign_id", "activista_id"])
    if not _index_exists("militantes", "ix_militantes_campaign_seccion"):
        op.create_index("ix_militantes_campaign_seccion", "militantes", ["campaign_id", "seccion"])
    if not _index_exists("militantes", "ix_militantes_campaign_estado"):
        op.create_index("ix_militantes_campaign_estado", "militantes", ["campaign_id", "estado"])
    if not _index_exists("militantes", "uq_militantes_campaign_folio"):
        op.create_index("uq_militantes_campaign_folio", "militantes", ["campaign_id", "folio"], unique=True)
    if not _index_exists("militantes", "uq_militantes_campaign_activista_client_uuid"):
        op.create_index("uq_militantes_campaign_activista_client_uuid", "militantes",
                        ["campaign_id", "activista_id", "client_uuid"], unique=True)
    if not _column_exists("campaigns", "meta_afiliacion"):
        op.add_column("campaigns", sa.Column("meta_afiliacion", sa.Integer(), nullable=True))

    # Generalize privacy_acceptances so it can reference a militante, not only a
    # registro: add nullable militante_id (plain column, no FK — trail survives
    # hard-delete) and relax registro_id NOT NULL.
    if _table_exists("privacy_acceptances"):
        if not _column_exists("privacy_acceptances", "militante_id"):
            op.add_column("privacy_acceptances", sa.Column("militante_id", sa.String(36), nullable=True))
            if not _index_exists("privacy_acceptances", "ix_privacy_acceptances_militante_id"):
                op.create_index("ix_privacy_acceptances_militante_id", "privacy_acceptances", ["militante_id"])
        # Drop NOT NULL on registro_id. Postgres does a simple ALTER; SQLite's
        # create_all path already has it nullable via the model, so skip there.
        if op.get_bind().dialect.name == "postgresql":
            reg = next((c for c in _insp().get_columns("privacy_acceptances")
                        if c["name"] == "registro_id"), None)
            if reg is not None and not reg["nullable"]:
                op.alter_column("privacy_acceptances", "registro_id",
                                existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    if _column_exists("privacy_acceptances", "militante_id"):
        if _index_exists("privacy_acceptances", "ix_privacy_acceptances_militante_id"):
            op.drop_index("ix_privacy_acceptances_militante_id", table_name="privacy_acceptances")
        op.drop_column("privacy_acceptances", "militante_id")
    if _column_exists("campaigns", "meta_afiliacion"):
        op.drop_column("campaigns", "meta_afiliacion")
    if _table_exists("militantes"):
        op.drop_table("militantes")
