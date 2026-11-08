"""Consent ledger (DPDP Act 2023, s.6; DPDP Rules 2025, Rule 3).

A standalone notice per purpose, in the owner's language; each choice stored with the
notice version, channel and time; withdrawal in one tap, as easy as giving it.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import AuditLog, Consent, now

NOTICE_VERSION = "2026-11-v2"

PURPOSES = {
    "kyc_verification": {"required": True, "data": ["GSTIN", "Udyam number", "4 document photos", "signatory name and ID number"],
                          "use": "Check your business with the GST and Udyam registries and verify your documents.",
                          "retention": "Photos deleted 30 days after verification; extracted fields kept, encrypted, for the contract term."},
    "ai_document_reading": {"required": False, "data": ["photos of business documents: GST, Udyam, shop licence, bill (never ID cards)"],
                            "use": "An AI service (Anthropic, outside India) reads your business documents to fill your details. "
                                   "Say no and our own reader plus a person check them instead.",
                            "retention": "Not used to train AI; kept by the provider only under its retention terms."},
    "service_delivery": {"required": True, "data": ["business address", "contact number"],
                          "use": "Install and activate your services and bill you.",
                          "retention": "For the contract term and as telecom licence rules require."},
    "order_updates": {"required": False, "data": ["contact number"],
                       "use": "Send order updates on WhatsApp and let a partner call you if you get stuck.",
                       "retention": "Until the order is live, or you withdraw."},
    "marketing": {"required": False, "data": ["contact number", "business type"],
                   "use": "Offers on other Dukaan Connect products.", "retention": "Until you withdraw."},
}


def record(db: Session, order_id: str, choices: dict[str, bool], language: str, channel: str) -> list[Consent]:
    missing = [p for p, meta in PURPOSES.items() if meta["required"] and not choices.get(p)]
    if missing:
        raise ValueError(f"required purposes not accepted: {missing}")
    rows = []
    for purpose in PURPOSES:
        c = Consent(order_id=order_id, purpose=purpose, granted=bool(choices.get(purpose)), notice_version=NOTICE_VERSION,
                    language=language, channel=channel)
        db.add(c)
        rows.append(c)
    db.add(AuditLog(actor="owner", action="consent_given", target=order_id, purpose=None, detail={k: bool(v) for k, v in choices.items()}))
    db.flush()
    return rows


def current(db: Session, order_id: str) -> dict[str, dict]:
    rows = db.scalars(select(Consent).where(Consent.order_id == order_id).order_by(Consent.id)).all()
    out: dict[str, dict] = {}
    for c in rows:
        out[c.purpose] = {"granted": c.granted and c.withdrawn_at is None, "since": c.created_at.isoformat(),
                          "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None, "notice_version": c.notice_version}
    return out


def has_consent(db: Session, order_id: str, purpose: str) -> bool:
    return current(db, order_id).get(purpose, {}).get("granted", False)


def withdraw(db: Session, order_id: str, purpose: str) -> None:
    rows = db.scalars(select(Consent).where(Consent.order_id == order_id, Consent.purpose == purpose, Consent.withdrawn_at.is_(None))).all()
    for c in rows:
        c.withdrawn_at = now()
    db.add(AuditLog(actor="owner", action="consent_withdrawn", target=order_id, purpose=purpose, detail={}))
    db.flush()
