"""Envelope encryption with AES-256-GCM.

Every record or file gets its own random data key (DEK). The DEK is wrapped by the
key-encryption key (KEK) derived from the master key, which in production lives in a
KMS (Google Cloud KMS / AWS KMS); here it comes from MASTER_KEY_B64.

Deleting a wrapped DEK makes the ciphertext permanently unreadable ("crypto-shredding"),
which is how retention deletes data even from backups.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from functools import lru_cache

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ..config import get_settings


def _derive(info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b"accel-udyam-v1", info=info).derive(get_settings().master_key())


@lru_cache
def _kek() -> bytes:
    return _derive(b"kek")


@lru_cache
def _hmac_key() -> bytes:
    return _derive(b"hmac-index")


def seal(plaintext: bytes, aad: bytes) -> tuple[bytes, bytes, bytes]:
    """Return (wrapped_dek, nonce, ciphertext). wrapped_dek = nonce12 || AESGCM(KEK, DEK)."""
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ct = AESGCM(dek).encrypt(nonce, plaintext, aad)
    wn = os.urandom(12)
    wrapped = wn + AESGCM(_kek()).encrypt(wn, dek, b"dek|" + aad)
    return wrapped, nonce, ct


def open_(wrapped_dek: bytes | None, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    if not wrapped_dek:
        raise PermissionError("data was crypto-shredded")
    wn, wct = wrapped_dek[:12], wrapped_dek[12:]
    dek = AESGCM(_kek()).decrypt(wn, wct, b"dek|" + aad)
    return AESGCM(dek).decrypt(nonce, ciphertext, aad)


def index(kind: str, value: str) -> str:
    """Keyed hash for lookups and de-duplication without storing the raw value."""
    return hmac.new(_hmac_key(), f"{kind}:{value.strip().upper()}".encode(), hashlib.sha256).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
