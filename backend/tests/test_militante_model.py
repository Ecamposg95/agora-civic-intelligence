"""Tests for the Militante model (formal party-member affiliation)."""
from app.models.militante import Militante
from app.models.organization import Organization
from tests.conftest import ALPHA_CAMPAIGN_ID, TestingSessionLocal, engine

# Militante isn't part of the fixed table list created by conftest.py's
# Base.metadata.create_all(engine, tables=[...]) call, so create it here.
Militante.__table__.create(bind=engine, checkfirst=True)


def test_militante_defaults_and_columns():
    db = TestingSessionLocal()
    try:
        org = db.query(Organization).filter_by(slug="alpha").one()
        m = Militante(
            organization_id=org.id,
            campaign_id=ALPHA_CAMPAIGN_ID,
            nombre_completo="Juan Pérez",
            folio="SMA-2027-00001",
            consentimiento=True,
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        assert m.id
        assert m.estado == "REGISTRADO"
        assert m.es_activista is False
        assert m.quality_flags is None or isinstance(m.quality_flags, dict)
    finally:
        db.query(Militante).delete()
        db.commit()
        db.close()
