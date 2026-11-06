"""People and promises: 'Talk to a person', staff sign-in, the KYC route, SIM users, My account."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data_store import store
from ..db import AdvisorSession, AuditLog, HelpRequest, Order, SimUser, get_db, now
from ..engine import schedule as payplan
from ..kyc.checks import ROUTES
from ..kyc.ids import mask_phone
from ..orders.service import add_event, complete_if_all_live
from ..privacy import vault
from ..security import login, staff
from .orders import PHONE, _events, activation_block, owner_order

router = APIRouter(prefix="/api", tags=["care"])

WINDOWS = {"asap": "within 2 working hours", "today_evening": "today, 6-9 pm", "tomorrow_morning": "tomorrow, 9-12",
           "tomorrow_evening": "tomorrow, 6-9 pm", "after_9pm": "after 9 pm today"}
REASONS = ("prefer_person", "price", "kyc_help", "install", "billing", "not_working", "other")
SIM_PRODUCTS = ("P07", "P08")


# ---- staff ---------------------------------------------------------------------------------

class LoginIn(BaseModel):
    user: str
    secret: str


@router.post("/staff/login")
def staff_login(body: LoginIn, db: Session = Depends(get_db)):
    out = login(body.user, body.secret)
    db.add(AuditLog(actor=f"{out['role']}:{out['sub']}", action="staff_login", target=out["sub"], purpose=None, detail={}))
    db.commit()
    return out


@router.get("/staff/me")
def me(who: dict = Depends(staff())):
    return who


# ---- talk to a person ------------------------------------------------------------------------

class HelpIn(BaseModel):
    phone: str
    window: str = "asap"
    reason: str = "prefer_person"
    language: str = "en"
    source: str = "advisor"
    session_id: str | None = None
    order_id: str | None = None
    key: str | None = None
    note: str | None = Field(default=None, max_length=300)


def _summary(db: Session, session_id: str | None, order: Order | None) -> tuple[dict, str | None]:
    """What the agent needs to pick up where the owner left off: masked facts, no identifiers."""
    if order:
        p = order.profile or {}
        return {"stage": order.status, "business_type": p.get("business_type"), "city": order.city, "segment": order.segment,
                "monthly": order.monthly, "products": [ln["name"] for ln in order.bundle.get("lines", [])],
                "kyc_route": p.get("kyc_route"), "kyc_outcome": order.kyc_outcome}, order.partner_id
    s = db.get(AdvisorSession, session_id) if session_id else None
    if s:
        p = {k: v for k, v in (s.profile or {}).items() if k != "_meta"}
        last = [m["text"] for m in (s.messages or []) if m["role"] == "user"][-3:]
        return {"stage": s.status, "business_type": p.get("business_type"), "city": p.get("city"), "employees": p.get("employees"),
                "has_gstin": p.get("has_gstin"), "needs": p.get("needs"), "budget": p.get("budget"),
                "monthly": (s.bundle or {}).get("monthly"), "products": [ln["name"] for ln in (s.bundle or {}).get("lines", [])],
                "last_messages": last}, s.partner_id
    return {}, None


@router.post("/help")
def ask_for_help(body: HelpIn, db: Session = Depends(get_db)):
    phone = re.sub(r"[\s-]", "", body.phone)
    if not PHONE.match(phone):
        raise HTTPException(422, "Enter a 10-digit Indian mobile number")
    if body.window not in WINDOWS:
        raise HTTPException(422, "Pick a time window")
    order = owner_order(db, body.order_id, body.key) if body.order_id else None
    summary, partner_id = _summary(db, body.session_id, order)
    if body.note:
        summary["note"] = body.note
    h = HelpRequest(source=body.source, session_id=body.session_id, order_id=order.id if order else None,
                    phone_token=vault.tokenize(db, "phone", phone[-10:]), language=body.language, window=body.window,
                    reason=body.reason if body.reason in REASONS else "other", summary=summary, partner_id=partner_id)
    db.add(h)
    db.flush()
    if order:
        add_event(db, order, "help_requested", "You asked for a call back", window=WINDOWS[body.window])
    if body.session_id and (s := db.get(AdvisorSession, body.session_id)):
        s.stall_reason = "asked_for_person"
    db.add(AuditLog(actor="owner", action="help_requested", target=h.id, purpose="service_delivery", detail={"window": body.window}))
    db.commit()
    return {"id": h.id, "status": h.status, "window": WINDOWS[body.window], "phone_masked": mask_phone(phone),
            "language": body.language}


@router.get("/help/{hid}")
def help_status(hid: str, db: Session = Depends(get_db)):
    h = db.get(HelpRequest, hid)
    if not h:
        raise HTTPException(404, "not found")
    return {"id": h.id, "status": h.status, "window": WINDOWS.get(h.window, h.window), "updated_at": h.updated_at.isoformat()}


@router.get("/backoffice/help")
def help_queue(db: Session = Depends(get_db), who: dict = Depends(staff("partner", "ops", "reviewer"))):
    q = select(HelpRequest).order_by(HelpRequest.created_at.desc()).limit(100)
    if who["role"] == "partner":  # partners see their own customers and unassigned requests
        q = q.where((HelpRequest.partner_id == who["partner_id"]) | (HelpRequest.partner_id.is_(None)))
    rows = db.scalars(q).all()
    return [{"id": h.id, "created_at": h.created_at.isoformat(), "source": h.source, "language": h.language,
             "window": WINDOWS.get(h.window, h.window), "reason": h.reason, "status": h.status, "assignee": h.assignee,
             "summary": h.summary, "order_id": h.order_id, "phone": "masked; call through the bridge"} for h in rows]


class HelpUpdate(BaseModel):
    status: str  # assigned | called | resolved
    note: str | None = None


@router.post("/backoffice/help/{hid}")
def help_update(hid: str, body: HelpUpdate, db: Session = Depends(get_db), who: dict = Depends(staff("partner", "ops", "reviewer"))):
    h = db.get(HelpRequest, hid)
    if not h:
        raise HTTPException(404, "not found")
    if body.status not in ("assigned", "called", "resolved"):
        raise HTTPException(422, "status must be assigned, called or resolved")
    h.status, h.assignee, h.note = body.status, who["name"], body.note or h.note
    if who.get("partner_id") and not h.partner_id:
        h.partner_id = who["partner_id"]
    if h.order_id and (o := db.get(Order, h.order_id)):
        add_event(db, o, f"help_{body.status}", {"assigned": f"{who['name']} will call you", "called": "We called you",
                                                 "resolved": "Your request is resolved"}[body.status])
    db.add(AuditLog(actor=f"{who['role']}:{who['sub']}", action=f"help_{body.status}", target=h.id, purpose="service_delivery", detail={}))
    db.commit()
    return {"id": h.id, "status": h.status, "assignee": h.assignee}


# ---- KYC route ------------------------------------------------------------------------------

class RouteIn(BaseModel):
    route: str


@router.post("/orders/{oid}/kyc/route")
def choose_route(oid: str, body: RouteIn, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    if body.route not in ROUTES:
        raise HTTPException(422, f"route must be one of {', '.join(ROUTES)}")
    o.profile = {**(o.profile or {}), "kyc_route": body.route}
    gst_only = [ln["name"] for ln in o.bundle.get("lines", []) if store().products[ln["product_id"]].requires_gstin]
    db.commit()
    return {"route": body.route, "needs": {"gst": ["gst_certificate", "address_proof", "signatory_id"],
                                           "udyam": ["udyam_certificate", "address_proof", "signatory_id"],
                                           "shop_licence": ["shop_licence", "address_proof", "signatory_id"]}[body.route],
            "gst_only_products": gst_only if body.route != "gst" else []}


# ---- business SIM users (DoT end-user KYC) -----------------------------------------------------

class SimUserIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str


class SimUsersIn(BaseModel):
    users: list[SimUserIn]


def sim_lines(order: Order) -> list[tuple[str, int]]:
    return [(ln["product_id"], ln["qty"]) for ln in order.bundle.get("lines", []) if ln["product_id"] in SIM_PRODUCTS]


def sim_view(db: Session, order: Order) -> dict:
    users = db.scalars(select(SimUser).where(SimUser.order_id == order.id).order_by(SimUser.created_at)).all()
    needed = sum(q for _, q in sim_lines(order))
    return {"needed": needed, "verified": sum(u.status == "verified" for u in users),
            "users": [{"id": u.id, "product_id": u.product_id, "status": u.status, "invite": f"/sim/{u.id}",
                       "phone_masked": u.phone_masked}
                      for u in users]}


@router.get("/orders/{oid}/sim-users")
def list_sim_users(oid: str, key: str = Query(...), db: Session = Depends(get_db)):
    return sim_view(db, owner_order(db, oid, key))


@router.post("/orders/{oid}/sim-users")
def add_sim_users(oid: str, body: SimUsersIn, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    slots = [pid for pid, q in sim_lines(o) for _ in range(q)]
    existing = db.scalars(select(SimUser).where(SimUser.order_id == o.id)).all()
    if len(existing) + len(body.users) > len(slots):
        raise HTTPException(422, f"This order has {len(slots)} business SIM(s)")
    for i, u in enumerate(body.users):
        phone = re.sub(r"[\s-]", "", u.phone)
        if not PHONE.match(phone):
            raise HTTPException(422, f"{u.name}: enter a 10-digit Indian mobile number")
        db.add(SimUser(order_id=o.id, name_token=vault.tokenize(db, "name", u.name.strip()), phone_token=vault.tokenize(db, "phone", phone[-10:]),
                       phone_masked=mask_phone(phone[-10:]), product_id=slots[len(existing) + i]))
    add_event(db, o, "sim_users_invited", f"{len(body.users)} SIM user(s) invited to verify")
    db.commit()
    return sim_view(db, o)


@router.get("/sim/{uid}")
def sim_invite(uid: str, db: Session = Depends(get_db)):
    u = db.get(SimUser, uid)
    if not u:
        raise HTTPException(404, "invite not found")
    o = db.get(Order, u.order_id)
    return {"id": u.id, "business_name": o.business_name if o else None, "status": u.status,
            "product": store().products[u.product_id].name}


class SimVerifyIn(BaseModel):
    method: str = "digilocker"  # digilocker | aadhaar_ekyc (both mocked: the operator's approved e-KYC)
    consent: bool


@router.post("/sim/{uid}/verify")
def sim_verify(uid: str, body: SimVerifyIn, db: Session = Depends(get_db)):
    u = db.get(SimUser, uid)
    if not u:
        raise HTTPException(404, "invite not found")
    if not body.consent:
        raise HTTPException(403, "The SIM user's consent is needed for their KYC")
    if body.method not in ("digilocker", "aadhaar_ekyc"):
        raise HTTPException(422, "unknown method")
    u.status, u.method, u.verified_at = "verified", body.method, now()
    o = db.get(Order, u.order_id)
    add_event(db, o, "sim_user_verified", f"A SIM user verified ({store().products[u.product_id].name})", u.product_id)
    db.add(AuditLog(actor="sim_user", action="end_user_kyc", target=u.id, purpose="kyc_verification", detail={"method": body.method}))
    db.flush()
    events = _events(db, o)
    held = any(e.kind == "activation_hold" and e.product_id == u.product_id for e in events)
    live = any(e.kind == "product_active" and e.product_id == u.product_id for e in events)
    if held and not live and o.status in ("scheduled", "active") and activation_block(db, o, u.product_id) is None:
        add_event(db, o, "product_active", f"{store().products[u.product_id].name} is live", u.product_id)  # the last user verified: the SIMs switch on
        db.flush()
        complete_if_all_live(db, o)
    db.commit()
    return {"id": u.id, "status": u.status}


def sims_ready(db: Session, order: Order) -> bool:
    v = sim_view(db, order)
    return v["verified"] >= v["needed"]


# ---- My account: after go-live -------------------------------------------------------------------

@router.get("/orders/{oid}/account")
def account(oid: str, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    sched = o.bundle.get("schedule") or payplan.for_bundle(o.bundle, o.setup_emi)
    paid_rows = 1 if (o.payment or {}).get("status") == "captured" else 0
    next_row = sched["rows"][paid_rows] if paid_rows < len(sched["rows"]) else None
    events = _events(db, o)
    live = {e.product_id for e in events if e.kind == "product_active"}
    helps = db.scalars(select(HelpRequest).where(HelpRequest.order_id == o.id).order_by(HelpRequest.created_at.desc())).all()
    return {
        "order_id": o.id, "status": o.status, "business_name": o.business_name,
        "services": [{"product_id": ln["product_id"], "name": ln["name"], "qty": ln["qty"], "monthly": ln["monthly"],
                      "status": "live" if ln["product_id"] in live else "setting_up"} for ln in o.bundle.get("lines", [])],
        "bill": {"one_bill": True, "schedule_hash": sched["hash"], "next_debit_paise": next_row["total"] if next_row else None,
                 "next_debit_month": next_row["month"] if next_row else None, "monthly_paise": sched["monthly"],
                 "monthly_after_emi_paise": sched["monthly_after_emi"], "emi_months_left": max(0, sched["emi_months"] - paid_rows),
                 "lines": [{"name": ln["name"], "qty": ln["qty"], "monthly": ln["monthly"]} for ln in o.bundle.get("lines", [])],
                 "autopay": bool((o.payment or {}).get("autopay_mandate")), "mandate_limit_paise": (o.payment or {}).get("mandate_limit_paise")},
        "help": [{"id": h.id, "status": h.status, "window": WINDOWS.get(h.window, h.window), "reason": h.reason,
                  "created_at": h.created_at.isoformat()} for h in helps],
        "checkins": [{"when": "first bill", "what": "We explain your first bill line by line."},
                     {"when": "day 30", "what": "Is everything working? Wi-Fi coverage, speed, email set up."}],
        "setup_tasks": [t for t in (
            {"product_id": "P16", "task": "Set up email on your own domain"},
            {"product_id": "P15", "task": "Verify your WhatsApp Business profile with Meta"},
            {"product_id": "P14", "task": "Register your SMS sender ID (DLT)"},
            {"product_id": "P18", "task": "Build your 5-page website"},
        ) if t["product_id"] in {ln["product_id"] for ln in o.bundle.get("lines", [])}],
    }
