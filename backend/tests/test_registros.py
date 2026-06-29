"""Tests for the activist capture core (User extensions, Registro model)."""
from app.models.user import User, UserRole


def test_user_role_has_lider_and_activista():
    assert UserRole.LIDER.value == "lider"
    assert UserRole.ACTIVISTA.value == "activista"


def test_user_has_lider_and_seccion_columns():
    cols = User.__table__.c
    assert "lider_id" in cols
    assert "seccion" in cols
