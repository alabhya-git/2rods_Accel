"""Other people who must say yes, each through their own link and an Aadhaar e-sign.

* The owner, when staff placed the order. Only 41% of leads are owners: the manager or
  office admin starts, the owner commits. The owner approves from wherever they are; no
  visit, and what they approve (the payment schedule's hash) is what gets charged.
* The landlord, when the shop is rented and the electricity bill is in their name. Their
  e-signed name must match the bill; then KYC passes without a person's review.

The e-sign is mocked (a 6-digit OTP). In production it is an Aadhaar eSign from a licensed
eSign service provider, which returns the signer's name as UIDAI holds it.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import Approval, AuditLog, Order, SessionLocal, get_db, now
from ..engine import schedule as payplan
from ..kyc import service as kyc
from ..kyc.checks import same
from ..kyc.ids import mask_phone
from ..orders.service import add_event
from ..privacy import vault
from ..privacy.crypto import sha256
from .orders import PHONE, _events, owner_order

router = APIRouter(prefix="/api", tags=["approvals"])
TERMS_VERSION = "2026-11-terms-v1"


def schedule_hash(o: Order) -> str:
    return (o.bundle.get("schedule") or payplan.for_bundle(o.bundle, o.setup_emi))["hash"]


def link(a: Approval, o: Order) -> str:
    return f"/approve/{a.token}?lang={o.language}"


def approvals_view(db: Session, o: Order) -> list[dict]:
    rows = db.scalars(select(Approval).where(Approval.order_id == o.id).order_by(Approval.created_at)).all()
    return [{"id": a.id, "kind": a.kind, "status": a.status, "phone_masked": a.phone_masked, "link": link(a, o),
             "decided_at": a.decided_at.isoformat() if a.decided_at else None, "note": a.note} for a in rows]


def owner_block(db: Session, o: Order) -> str | None:
    """Why the order can't be charged yet because of the owner, or None."""
    a = db.scalar(select(Approval).where(Approval.order_id == o.id, Approval.kind == "owner").order_by(Approval.created_at.desc()))
    if not a:
        return None
    if a.status == "pending":
        return "Waiting for the owner to approve this order. We sent them a link."
    if a.status == "declined":
        return "The owner declined this order."
    if a.schedule_hash != schedule_hash(o):
        return "The order changed after the owner approved it. Send them the new version."
    return None


def _clean_phone(raw: str) -> str:
    phone = re.sub(r"[\s-]", "", raw or "")
    if not PHONE.match(phone):
        raise HTTPException(422, "Enter a 10-digit Indian mobile number")
    return phone[-10:]


def _order_phone(db: Session, o: Order) -> str | None:
    if not o.phone_token:
        return None
    return vault.detokenize(db, o.phone_token, "fulfilment", "service_delivery", o.id)


def request_owner(db: Session, o: Order, owner_phone: str, placed_by_phone: str) -> Approval:
    phone = _clean_phone(owner_phone)
    if phone == placed_by_phone:
        raise HTTPException(422, "The owner's number must be different from yours")
    a = Approval(order_id=o.id, kind="owner", phone_token=vault.tokenize(db, "phone", phone), phone_masked=mask_phone(phone))
    db.add(a)
    db.flush()
    add_event(db, o, "approval_requested", f"Sent to the owner ({a.phone_masked}) to approve", who="owner", masked=a.phone_masked)
    db.add(AuditLog(actor="staff_at_business", action="owner_approval_requested", target=a.id, purpose="service_delivery", detail={}))
    return a


# ---- the landlord ----------------------------------------------------------------------------

class LandlordIn(BaseModel):
    phone: str


@router.post("/orders/{oid}/landlord")
def ask_landlord(oid: str, body: LandlordIn, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    billed = (((o.kyc_result or {}).get("extracted") or {}).get("address_proof") or {}).get("billed_to")
    if not billed:
        raise HTTPException(409, "Upload the electricity bill first: the landlord confirms the name on it")
    phone = _clean_phone(body.phone)
    if phone == _order_phone(db, o):
        raise HTTPException(422, "The landlord confirms from their own phone, not yours")
    for old in db.scalars(select(Approval).where(Approval.order_id == o.id, Approval.kind == "landlord", Approval.status == "pending")):
        old.status, old.note = "declined", "replaced by a new request"
    a = Approval(order_id=o.id, kind="landlord", phone_token=vault.tokenize(db, "phone", phone), phone_masked=mask_phone(phone),
                 expected_name=billed)
    db.add(a)
    db.flush()
    add_event(db, o, "approval_requested", f"Sent to your landlord ({a.phone_masked}) to confirm the shop", who="landlord", masked=a.phone_masked)
    db.commit()
    return {"id": a.id, "status": a.status, "phone_masked": a.phone_masked, "link": link(a, o)}


# ---- the signer's page -----------------------------------------------------------------------

def _get(db: Session, token: str) -> tuple[Approval, Order]:
    a = db.scalar(select(Approval).where(Approval.token == token))
    o = db.get(Order, a.order_id) if a else None
    if not a or not o:
        raise HTTPException(404, "This link is not valid")
    return a, o


@router.get("/approvals/{token}")
def approval_page(token: str, db: Session = Depends(get_db)):
    a, o = _get(db, token)
    out = {"kind": a.kind, "status": a.status, "business_name": o.business_name, "language": o.language, "terms_version": TERMS_VERSION}
    if a.kind == "owner":
        s = o.bundle.get("schedule") or payplan.for_bundle(o.bundle, o.setup_emi)
        placed = next((e.detail.get("masked") for e in _events(db, o) if e.kind == "number_verified"), None)
        out |= {"prepared_by": placed, "lines": [{"name": ln["name"], "qty": ln["qty"], "monthly": ln["monthly"]} for ln in o.bundle.get("lines", [])],
                "monthly_paise": s["monthly"], "due_today_paise": s["due_today"], "term_months": s["term_months"],
                "total_commitment_paise": s["total_commitment"], "kyc_status": o.status}
    else:
        bill = ((o.kyc_result or {}).get("extracted") or {}).get("address_proof") or {}
        out |= {"name_on_bill": a.expected_name, "premises": bill.get("supply_address")}
    return out


class DecisionIn(BaseModel):
    decision: str  # approve | decline
    name: str = Field(default="", max_length=120)  # as on Aadhaar: what the eSign returns
    otp: str = ""
    consent: bool = False
    reason: str | None = Field(default=None, max_length=200)


@router.post("/approvals/{token}")
async def decide(token: str, body: DecisionIn):
    def work():
        db = SessionLocal()
        try:
            return _decide(db, token, body)
        finally:
            db.close()
    return await run_in_threadpool(work)  # a landlord's yes re-runs KYC, which may read documents


def _decide(db: Session, token: str, body: DecisionIn) -> dict:
    a, o = _get(db, token)
    if a.status != "pending":
        raise HTTPException(409, f"Already {a.status}")
    who = "The owner" if a.kind == "owner" else "Your landlord"
    if body.decision == "decline":
        a.status, a.decided_at, a.note = "declined", now(), body.reason
        add_event(db, o, f"{a.kind}_declined", f"{who} said no" + (f": {body.reason}" if body.reason else ""))
        db.add(AuditLog(actor=a.kind, action="approval_declined", target=a.id, purpose="service_delivery", detail={}))
        db.commit()
        return {"status": a.status}
    if body.decision != "approve":
        raise HTTPException(422, "decision must be approve or decline")
    if not body.consent:
        raise HTTPException(403, "Tick the box to agree first")
    if not re.fullmatch(r"\d{6}", body.otp or ""):
        raise HTTPException(422, "Enter the 6-digit OTP sent to your Aadhaar-linked mobile")
    name = body.name.strip()
    if len(name) < 3:
        raise HTTPException(422, "Enter your name as on Aadhaar")
    if a.kind == "landlord" and not same(name, a.expected_name):
        raise HTTPException(422, "The name on your Aadhaar must match the name on the electricity bill")
    a.status, a.decided_at, a.method = "approved", now(), "aadhaar_esign (mock)"
    a.name_token = vault.tokenize(db, "name", name)
    a.terms_version = TERMS_VERSION
    a.schedule_hash = schedule_hash(o) if a.kind == "owner" else None
    a.signature = sha256(f"{a.id}|{a.schedule_hash}|{a.terms_version}|{a.decided_at.isoformat()}".encode())
    db.add(AuditLog(actor=a.kind, action="approval_esigned", target=a.id, purpose="service_delivery",
                    detail={"terms": a.terms_version, "schedule_hash": a.schedule_hash, "signature": a.signature}))
    out = {"status": a.status, "signature": a.signature[:12]}
    if a.kind == "owner":
        add_event(db, o, "owner_approved", "The owner approved with Aadhaar e-sign", terms=a.terms_version, schedule_hash=a.schedule_hash)
        out |= {"order_id": o.id, "access_key": o.access_key}  # the owner's phone now holds the order too
    else:
        add_event(db, o, "landlord_confirmed", "Your landlord confirmed the shop is let to you")
        db.flush()
        if o.status in ("kyc_pending", "kyc_fix", "kyc_review"):
            try:
                out["kyc"] = kyc.run(db, o).outcome  # the bill now proves the address: no one needs to look
            except PermissionError:  # the business withdrew KYC consent: their next check picks this up
                pass
    db.commit()
    return out
