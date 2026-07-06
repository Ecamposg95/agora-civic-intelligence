"""Tests for retention_service.purge_expired purging Militante bucket objects.

Task 10: hard-deleting militantes must also delete their INE photo + signature
objects from the bucket. Mirrors the Registro Pass A (soft-delete age) pattern
in test_retention.py, applied to Militante.

TDD: written before the implementation change (see retention_service.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.config import settings as app_settings
from app.models.militante import Militante
from app.schemas.militante import MilitanteCreate
from app.services import militante_service, retention_service

_NOW = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
_LONG_AGO = datetime(2000, 1, 1, tzinfo=timezone.utc)


def _retention_patches():
    return (
        patch.object(app_settings, "RETENTION_ENABLED", True),
        patch.object(app_settings, "RETENTION_PURGE_SOFT_DELETED_DAYS", 30),
        patch.object(app_settings, "RETENTION_DAYS_AFTER_ELECTION", 180),
    )


def test_purge_deletes_militante_docs(db_session, activista_ctx, monkeypatch):
    """Hard-purging a soft-deleted militante deletes its bucket objects first."""
    import app.core.storage as storage

    deleted: list[str] = []
    monkeypatch.setattr(storage, "storage_enabled", lambda: True)
    monkeypatch.setattr(storage, "put_object", lambda *a, **k: None)
    monkeypatch.setattr(storage, "delete_object", lambda key: deleted.append(key))

    m = militante_service.create_militante(
        db_session, activista_ctx,
        MilitanteCreate(nombre_completo="Purge Test", consentimiento=True, seccion="4127"),
    )
    militante_service.upload_documento(db_session, activista_ctx, m.id, "frente", b"x", "image/jpeg")
    militante_service.upload_documento(db_session, activista_ctx, m.id, "firma", b"y", "image/png")

    m.deleted_at = _LONG_AGO
    db_session.commit()

    p1, p2, p3 = _retention_patches()
    with p1, p2, p3:
        result = retention_service.purge_expired(db_session, now=_NOW)

    assert result.militantes_soft_deleted_purged == 1
    assert any(k.endswith("/frente.jpg") for k in deleted), deleted
    assert any(k.endswith("/firma.png") for k in deleted), deleted

    db_session.expire_all()
    assert db_session.get(Militante, m.id) is None


def test_purge_skips_storage_calls_when_storage_disabled(db_session, activista_ctx, monkeypatch):
    """When storage_enabled() is False, the row is still hard-purged but no
    storage.delete_object calls are made (mirrors storage.py's feature gate)."""
    import app.core.storage as storage

    calls: list[str] = []
    monkeypatch.setattr(storage, "storage_enabled", lambda: False)
    monkeypatch.setattr(storage, "put_object", lambda *a, **k: None)
    monkeypatch.setattr(storage, "delete_object", lambda key: calls.append(key))

    m = militante_service.create_militante(
        db_session, activista_ctx,
        MilitanteCreate(nombre_completo="Purge Test 2", consentimiento=True, seccion="4127"),
    )
    militante_service.upload_documento(db_session, activista_ctx, m.id, "frente", b"x", "image/jpeg")

    m.deleted_at = _LONG_AGO
    db_session.commit()

    p1, p2, p3 = _retention_patches()
    with p1, p2, p3:
        result = retention_service.purge_expired(db_session, now=_NOW)

    assert result.militantes_soft_deleted_purged == 1
    assert calls == []

    db_session.expire_all()
    assert db_session.get(Militante, m.id) is None


def test_purge_continues_when_delete_object_raises(db_session, activista_ctx, monkeypatch):
    """A failing storage.delete_object must not abort the purge of the row."""
    import app.core.storage as storage

    def _boom(key):
        raise RuntimeError("simulated network blip")

    monkeypatch.setattr(storage, "storage_enabled", lambda: True)
    monkeypatch.setattr(storage, "put_object", lambda *a, **k: None)
    monkeypatch.setattr(storage, "delete_object", _boom)

    m = militante_service.create_militante(
        db_session, activista_ctx,
        MilitanteCreate(nombre_completo="Purge Test 3", consentimiento=True, seccion="4127"),
    )
    militante_service.upload_documento(db_session, activista_ctx, m.id, "frente", b"x", "image/jpeg")
    militante_service.upload_documento(db_session, activista_ctx, m.id, "reverso", b"z", "image/jpeg")

    m.deleted_at = _LONG_AGO
    db_session.commit()

    p1, p2, p3 = _retention_patches()
    with p1, p2, p3:
        result = retention_service.purge_expired(db_session, now=_NOW)

    assert result.militantes_soft_deleted_purged == 1
    db_session.expire_all()
    assert db_session.get(Militante, m.id) is None


def test_purge_does_not_touch_active_militante(db_session, activista_ctx, monkeypatch):
    """A militante without deleted_at set must survive the soft-delete pass."""
    import app.core.storage as storage

    deleted: list[str] = []
    monkeypatch.setattr(storage, "storage_enabled", lambda: True)
    monkeypatch.setattr(storage, "put_object", lambda *a, **k: None)
    monkeypatch.setattr(storage, "delete_object", lambda key: deleted.append(key))

    m = militante_service.create_militante(
        db_session, activista_ctx,
        MilitanteCreate(nombre_completo="Still Active", consentimiento=True, seccion="4127"),
    )
    militante_service.upload_documento(db_session, activista_ctx, m.id, "frente", b"x", "image/jpeg")

    p1, p2, p3 = _retention_patches()
    with p1, p2, p3:
        result = retention_service.purge_expired(db_session, now=_NOW)

    assert result.militantes_soft_deleted_purged == 0
    assert deleted == []

    db_session.expire_all()
    assert db_session.get(Militante, m.id) is not None
