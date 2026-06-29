"""Tests for RBAC v2: new UserRole values and User.coordinador_id column."""

from app.models.user import User, UserRole


def test_new_roles_exist():
    assert UserRole.COORDINADOR.value == "coordinador"
    assert UserRole.CAPTURISTA.value == "capturista"
    assert UserRole.CONSULTA.value == "consulta"


def test_user_has_coordinador_id():
    assert "coordinador_id" in User.__table__.c
