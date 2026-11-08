from __future__ import annotations

import statistics

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..backoffice import propensity
from ..config import get_settings
from ..data_store import store
from ..db import AdvisorSession, AuditLog, Callback, Order, OrderEvent, get_db
from ..network.telco import masked_number
from ..orders.service import add_event
from ..privacy.consent import has_consent
from ..security import staff

router = APIRouter(prefix="/api/backoffice", tags=["backoffice"])


partner = staff("partner", "ops", "reviewer")  # any signed-in staff member
reviewer = staff("reviewer")

# failures a single reviewer may not wave through: a second, different reviewer must agree
TWO_PERSON = {"gstin.registry", "gst_certificate.gstin", "gst_certificate.legal_name", "gst_certificate.trade_name",
              "signatory.business", "signatory.proprietor", "address_proof.future", "address_proof.address", "udyam.name",
              "signatory.sim_swap"}
NEVER_OVERRIDE = {"gstin.status", "bundle.gst_only"}  # an inactive GSTIN is fixed by changing the order, not by approval


@router.get("/leads")
def leads(limit: int = 40, segment: str | None = None, city: str | None = None, reason: str | None = None, _: dict = Depends(partner)):
    return {"model": {k: v for k, v in propensity.card().items() if k in ("auc", "top30_share", "top_decile_rate", "base_rate")},
            "leads": propensity.queue(limit, segment, city, reason),
            "reasons": sorted({r["drop_reason"] for r in store().leads if r["drop_reason"]})}


@router.get("/model")
def model_card(_: dict = Depends(partner)):
    return propensity.card()


@router.post("/leads/{lead_id}/call")
def call_lead(lead_id: str, db: Session = Depends(get_db), who: dict = Depends(partner)):
    if not any(r["lead_id"] == lead_id for r in store().leads):
        raise HTTPException(404, "lead not found")
    num = masked_number()
    pid = who.get("partner_id") or who["sub"]
    cb = Callback(lead_id=lead_id, partner_id=pid, status="called", virtual_number=num)
    db.add(cb)
    db.add(AuditLog(actor=f"{who['role']}:{who['sub']}", action="masked_call", target=lead_id, purpose="order_updates", detail={"virtual": num}))
    db.commit()
    return {"virtual_number": num, "valid_hours": 72, "note": "Bridged through Dukaan Connect CPaaS; the customer's real number is never shown."}


@router.get("/orders")
def orders(db: Session = Depends(get_db), who: dict = Depends(partner)):
    q = select(Order).order_by(Order.created_at.desc()).limit(100)
    if who["role"] == "partner":  # a partner sees only the orders credited to them
        q = q.where(Order.partner_id == who.get("partner_id"))
    rows = db.scalars(q).all()
    return [{"id": o.id, "business_name": o.business_name, "segment": o.segment, "city": o.city, "status": o.status, "monthly": o.monthly,
             "kyc_outcome": o.kyc_outcome, "partner_id": o.partner_id, "channel": o.channel, "language": o.language,
             "created_at": o.created_at.isoformat(), "specimen": o.specimen} for o in rows]


@router.get("/reviews")
def reviews(db: Session = Depends(get_db), _: dict = Depends(reviewer)):
    rows = db.scalars(select(Order).where(Order.status.in_(["kyc_review", "kyc_fix"])).order_by(Order.updated_at.desc())).all()
    out = []
    for o in rows:
        fails = [c for c in (o.kyc_result or {}).get("checks", []) if c["status"] == "fail"]
        out.append({"id": o.id, "business_name": o.business_name, "status": o.status, "specimen": o.specimen,
                    "route": (o.kyc_result or {}).get("route"), "failed_checks": fails, "registry": (o.kyc_result or {}).get("registry"),
                    "pending_approval": (o.profile or {}).get("pending_approval"),
                    "needs_two_reviewers": any(c["id"] in TWO_PERSON for c in fails),
                    "cannot_approve": sorted({c["id"] for c in fails} & NEVER_OVERRIDE)})
    return out


class ReviewIn(BaseModel):
    decision: str  # approve | reject | ask_fix
    note: str | None = Field(default=None, max_length=500)


@router.post("/orders/{oid}/review")
def review(oid: str, body: ReviewIn, db: Session = Depends(get_db), who: dict = Depends(reviewer)):
    """A reviewer's decision. Approval only from review, with consent and a full document set;
    risky overrides need a second reviewer; an inactive GSTIN can't be approved at all."""
    o = db.get(Order, oid)
    if not o:
        raise HTTPException(404, "order not found")
    if o.status not in ("kyc_review", "kyc_fix"):
        raise HTTPException(409, f"order is {o.status}, not waiting for review")
    fails = {c["id"] for c in (o.kyc_result or {}).get("checks", []) if c["status"] == "fail"}
    actor = f"{who['role']}:{who['sub']}"
    if body.decision == "approve":
        if not has_consent(db, o.id, "kyc_verification"):
            raise HTTPException(409, "no KYC consent on this order")
        if not o.kyc_result or o.status != "kyc_review":
            raise HTTPException(409, "only applications in review can be approved; ask the owner to fix first")
        if fails & NEVER_OVERRIDE:
            raise HTTPException(409, "an inactive GSTIN can't be approved; offer the non-GST route instead")
        if any(c.endswith(".present") or c.endswith(".legible") or c.endswith(".type") or c.endswith(".fields") for c in fails):
            raise HTTPException(409, "a document is missing or unreadable; ask the owner to fix it")
        pending = (o.profile or {}).get("pending_approval")
        if fails & TWO_PERSON and not pending:
            o.profile = {**(o.profile or {}), "pending_approval": who["sub"]}
            db.add(AuditLog(actor=actor, action="kyc_approve_first", target=o.id, purpose="kyc_verification", detail={"note": body.note}))
            db.commit()
            return {"status": o.status, "pending_approval": who["sub"], "message": "A second reviewer must confirm this approval"}
        if pending and pending == who["sub"]:
            raise HTTPException(409, "a different reviewer must confirm")
        o.status, o.kyc_outcome = "kyc_verified", "verified"
        o.profile = {k: v for k, v in (o.profile or {}).items() if k != "pending_approval"}
        add_event(db, o, "kyc_verified", "KYC verified by our team", reviewers=[x for x in (pending, who["sub"]) if x])
    elif body.decision == "reject":
        o.status = "cancelled"
        add_event(db, o, "kyc_rejected", "We could not verify the documents")
    elif body.decision == "ask_fix":
        o.status = "kyc_fix"
        add_event(db, o, "kyc_fix", body.note or "Please re-upload the flagged document")
    else:
        raise HTTPException(422, "decision must be approve, reject or ask_fix")
    o.review_note = body.note
    db.add(AuditLog(actor=actor, action=f"kyc_{body.decision}", target=o.id, purpose="kyc_verification", detail={"note": body.note}))
    db.commit()
    return {"status": o.status}


@router.get("/sessions")
def stalled_sessions(db: Session = Depends(get_db), _: dict = Depends(partner)):
    rows = db.scalars(select(AdvisorSession).where(AdvisorSession.status.in_(["open", "quoted"])).order_by(AdvisorSession.updated_at.desc()).limit(50)).all()
    out = []
    for s in rows:
        p = {k: v for k, v in (s.profile or {}).items() if k != "_meta"}
        try:
            score = round(propensity.score_profile(p), 3)
        except Exception:  # noqa: BLE001
            score = None
        out.append({"session_id": s.id, "status": s.status, "language": s.language, "channel": s.channel, "partner_id": s.partner_id,
                    "business_type": p.get("business_type"), "city": p.get("city"), "employees": p.get("employees"),
                    "monthly": (s.bundle or {}).get("monthly"), "score": score, "stall_reason": s.stall_reason,
                    "updated_at": s.updated_at.isoformat()})
    return out


@router.get("/metrics")
def metrics(db: Session = Depends(get_db), _: dict = Depends(partner)):
    leads = store().leads
    act = [r for r in leads if r["outcome"] == "Activated"]
    baseline = {
        "leads": len(leads), "activated": len(act), "conversion": round(len(act) / len(leads), 4),
        "days_to_activate": round(statistics.mean(int(r["days_lead_to_activation"]) for r in act), 1),
        "status_chases": round(statistics.mean(int(r["customer_follow_up_calls"]) for r in act), 2),
        "cost_per_activation": round(sum(int(r["acquisition_cost_inr"]) for r in leads) / len(act)),
        "churn_6m": round(sum(r["churned_within_6_months"] == "Y" for r in act) / len(act), 3),
    }
    sessions = db.scalar(select(func.count()).select_from(AdvisorSession)) or 0
    quoted = db.scalar(select(func.count()).select_from(AdvisorSession).where(AdvisorSession.status.in_(["quoted", "ordered"]))) or 0
    orders = db.scalars(select(Order)).all()
    auto = sum(1 for o in orders if o.kyc_outcome == "verified")
    kyc_done = sum(1 for o in orders if o.kyc_outcome)
    minutes = []
    for o in orders:
        s = db.get(AdvisorSession, o.session_id) if o.session_id else None
        if s:
            minutes.append((o.created_at - s.created_at).total_seconds() / 60)
    live = {"sessions": sessions, "quoted": quoted, "orders": len(orders), "active": sum(o.status == "active" for o in orders),
            "kyc_auto_verified_share": round(auto / kyc_done, 3) if kyc_done else None,
            "median_minutes_chat_to_order": round(statistics.median(minutes), 1) if minutes else None,
            "status_chase_calls": 0}
    targets = {"conversion": 0.15, "days_to_activate": 7, "cost_per_activation": 4000, "status_chases": 0.5, "churn_6m": 0.10}
    return {"baseline": baseline, "live": live, "targets": targets}
