"""Territorio + promovidos — modelos, scope, asignación, tabla."""
from app.models.user import User
from app.models.registro import Registro
from app.models.seccion_electoral import SeccionElectoral


def test_models_have_new_columns():
    assert "area_id" in User.__table__.columns
    assert "promotor" in Registro.__table__.columns
    cols = set(SeccionElectoral.__table__.columns.keys())
    assert {"seccion", "municipio", "anio", "lista_nominal", "votos",
            "participacion", "coalicion", "morena", "margen", "prioridad"}.issubset(cols)


def test_seccion_electoral_table_is_created():
    from tests.conftest import TestingSessionLocal
    from app.models.seccion_electoral import SeccionElectoral
    db = TestingSessionLocal()
    try:
        db.add(SeccionElectoral(seccion="0001", anio=2024, margen=10, prioridad="COMPETITIVA"))
        db.commit()
        from sqlalchemy import select
        row = db.execute(select(SeccionElectoral).where(SeccionElectoral.seccion == "0001")).scalar_one()
        assert row.anio == 2024 and row.prioridad == "COMPETITIVA"
    finally:
        db.close()
