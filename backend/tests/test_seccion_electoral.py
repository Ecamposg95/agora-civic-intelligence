"""Seed de territorio demo — San Mateo Atenco + matriz seccional 2024."""
from sqlalchemy import func, select

from app.models.electoral_area import AreaLevel, ElectoralArea
from app.models.seccion_electoral import SeccionElectoral
from app.seeds.demo_territory import seed_demo_territory
from tests.conftest import TestingSessionLocal


def test_seed_creates_municipio_secciones_and_matrix():
    db = TestingSessionLocal()
    try:
        seed_demo_territory(db)
        muni = db.execute(select(ElectoralArea).where(
            ElectoralArea.code == "15076")).scalar_one()
        assert muni.level == AreaLevel.MUNICIPIO
        n_sec = db.execute(select(func.count()).select_from(ElectoralArea).where(
            ElectoralArea.level == AreaLevel.SECCION,
            ElectoralArea.municipio_id == muni.id)).scalar_one()
        assert n_sec == 22
        n_fact = db.execute(select(func.count()).select_from(SeccionElectoral).where(
            SeccionElectoral.anio == 2024)).scalar_one()
        assert n_fact == 22
        row = db.execute(select(SeccionElectoral).where(
            SeccionElectoral.seccion == "4121")).scalar_one()
        assert row.margen == -115 and row.prioridad == "COMPETITIVA"
    finally:
        db.close()


def test_seed_is_idempotent():
    db = TestingSessionLocal()
    try:
        seed_demo_territory(db)
        seed_demo_territory(db)
        n = db.execute(select(func.count()).select_from(SeccionElectoral)).scalar_one()
        assert n == 22
        n_area = db.execute(select(func.count()).select_from(ElectoralArea).where(
            ElectoralArea.code == "15076")).scalar_one()
        assert n_area == 1
    finally:
        db.close()
