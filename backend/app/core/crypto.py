"""Encryption helpers for sensitive fields (clave de elector).

Enfoque B: the service stores ciphertext + a masked display value. Decryption
exists only for the SPA-2 reveal flow (with audit) — not used in SPA-1.
The app fails fast if FERNET_KEY is missing: never store PII in clear.
"""
from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings


@lru_cache(maxsize=1)
def _build_fernet() -> Fernet:
    key = settings.FERNET_KEY
    if not key:
        raise RuntimeError(
            "FERNET_KEY is not set. Refusing to handle clave de elector without "
            "encryption. Set FERNET_KEY in the environment."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def ensure_crypto_ready() -> None:
    """Validate the Fernet key at startup. Raises RuntimeError if misconfigured."""
    _build_fernet()


def encrypt_clave(plain: str) -> bytes:
    """Encrypt a clave de elector. Returns ciphertext bytes."""
    return _build_fernet().encrypt(plain.encode())


def decrypt_clave(ct: bytes) -> str:
    """Decrypt ciphertext back to the clave. SPA-2 reveal only."""
    return _build_fernet().decrypt(ct).decode()


def mask_clave(plain: str) -> str:
    """Return a masked display value, e.g. ``****-XYZ8``."""
    return f"****-{plain[-4:]}"
