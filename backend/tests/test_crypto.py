"""Tests for app.core.crypto (Fernet encryption of clave de elector)."""
import pytest

from app.core import crypto


def test_encrypt_decrypt_round_trip():
    ct = crypto.encrypt_clave("ABCD1234567890XYZ8")
    assert isinstance(ct, bytes)
    assert ct != b"ABCD1234567890XYZ8"
    assert crypto.decrypt_clave(ct) == "ABCD1234567890XYZ8"


def test_mask_clave_shows_last_four():
    assert crypto.mask_clave("ABCD1234567890XYZ8") == "****-XYZ8"


def test_mask_clave_short_value():
    assert crypto.mask_clave("12") == "****-12"


def test_encrypt_fails_without_key(monkeypatch):
    monkeypatch.setattr(crypto.settings, "FERNET_KEY", "")
    crypto._build_fernet.cache_clear()
    with pytest.raises(RuntimeError):
        crypto.encrypt_clave("ABCD1234567890XYZ8")
    crypto._build_fernet.cache_clear()  # restore for other tests
