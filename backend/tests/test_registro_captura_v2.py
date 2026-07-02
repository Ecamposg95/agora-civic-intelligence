"""Captura v2 — nuevos campos + vista de equipo (activista_nombre, scope, coordinador read)."""
from app.models.registro import Registro


def test_registro_model_has_captura_v2_columns():
    cols = set(Registro.__table__.columns.keys())
    assert {"sexo", "edad", "estructura", "observacion"}.issubset(cols)
