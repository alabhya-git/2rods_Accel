"""Token vault: raw identifiers enter once and are replaced by random tokens.

Services, the advisor LLM, analytics and the back-office only ever handle tokens or
masked values. Detokenising needs an allowed (actor, purpose) pair, a live consent for
that purpose, and leaves an audit record.
"""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import AuditLog, VaultEntry
from . import crypto
from .consent import has_consent

KINDS = ("gstin", "udyam", "phone", "email", "id_no", "address", "name")

# who may see raw values, and for what
POLICY: dict[str, set[str]] = {
    "kyc_service": {"kyc_verification"},
    "fulfilment": {"service_delivery"},
    "owner": {"rights_access"},
    "messaging": {"order_updates"},
}
ORDER_PURPOSES = {"kyc_verification", "service_delivery", "order_updates"}


def tokenize(db: Session, kind: str, value: str) -> str:
    """A fresh token per use. Tokens are never shared between orders, so erasing one
    order's data (crypto-shredding its tokens) can never break another order."""
    if kind not in KINDS:
        raise ValueError(kind)
    value = value.strip()
    idx = crypto.index(kind, value)
    token = f"tok_{kind}_{secrets.token_urlsafe(16)}"
    wrapped, nonce, ct = crypto.seal(value.encode(), aad=token.encode())
    db.add(VaultEntry(token=token, kind=kind, hmac_index=idx, wrapped_dek=wrapped, nonce=nonce, ciphertext=ct))
    db.flush()
    return token


def find(db: Session, kind: str, value: str) -> str | None:
    e = db.scalar(select(VaultEntry).where(VaultEntry.kind == kind, VaultEntry.hmac_index == crypto.index(kind, value)))
    return e.token if e else None


def detokenize(db: Session, token: str, actor: str, purpose: str, order_id: str | None = None) -> str:
    allowed = POLICY.get(actor, set())
    if purpose not in allowed:
        db.add(AuditLog(actor=actor, action="detokenize_denied", target=token[:20], purpose=purpose, detail={"reason": "policy"}))
        db.flush()
        raise PermissionError(f"{actor} may not detokenise for {purpose}")
    if purpose in ORDER_PURPOSES and not order_id:  # consent is per order: no order, no check, no access
        db.add(AuditLog(actor=actor, action="detokenize_denied", target=token[:20], purpose=purpose, detail={"reason": "no_order"}))
        db.flush()
        raise PermissionError(f"{purpose} access needs the order it is for")
    if order_id and purpose != "rights_access" and not has_consent(db, order_id, purpose):
        db.add(AuditLog(actor=actor, action="detokenize_denied", target=token[:20], purpose=purpose, detail={"reason": "no_consent"}))
        db.flush()
        raise PermissionError(f"no live consent for {purpose}")
    e = db.get(VaultEntry, token)
    if not e:
        raise KeyError(token)
    value = crypto.open_(e.wrapped_dek, e.nonce, e.ciphertext, aad=token.encode()).decode()
    db.add(AuditLog(actor=actor, action="detokenize", target=token[:20], purpose=purpose, detail={"order": order_id}))
    db.flush()
    return value


def shred(db: Session, token: str) -> None:
    """Crypto-shred: drop the wrapped key; the ciphertext becomes unreadable everywhere."""
    e = db.get(VaultEntry, token)
    if e:
        e.wrapped_dek = None
        db.add(AuditLog(actor="system", action="shred", target=token[:20], purpose=None, detail={}))
        db.flush()
