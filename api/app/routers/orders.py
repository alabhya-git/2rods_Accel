from __future__ import annotations

import asyncio
import json
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from ..config import get_settings
from ..data_store import lookup_gstin, store
from ..db import AdvisorSession, AuditLog, Document, Order, OrderEvent, SessionLocal, get_db, now
from ..engine import schedule as payplan
from ..engine.profile import Profile
from ..engine.recommend import build_addons, price_custom
from ..kyc import service as kyc
from ..kyc.ids import gstin_valid, mask_gstin, mask_phone, udyam_valid
from ..network.telco import fibre_feasible, number_verify
from ..orders.events import bus
from ..orders.service import add_event, advance, complete_if_all_live, create_order, install_slots, public_view
from ..privacy import consent, vault
from ..privacy.storage import shred_document
from ..security import verify as verify_staff
from ..advisor.agent import reason_text, rule_text
from .advisor import load_state

router = APIRouter(prefix="/api", tags=["orders"])
PHONE = re.compile(r"^(?:\+?91)?[6-9]\d{9}$")


def owner_order(db: Session, oid: str, key: str | None) -> Order:
    o = db.get(Order, oid)
    if not o or (key != o.access_key):
        raise HTTPException(404, "order not found")
    return o


# ---- quote ------------------------------------------------------------------------

class QuoteIn(BaseModel):
    session_id: str | None = None
    profile: dict | None = None
    items: dict[str, int] = Field(default_factory=dict)
    term_months: int = 12
    language: str = "en"


def profile_for(db: Session, session_id: str | None, profile: dict | None) -> tuple[Profile, AdvisorSession | None]:
    s = db.get(AdvisorSession, session_id) if session_id else None
    if s:
        prof = Profile.from_dict(load_state(s)["profile"])
    else:
        prof = Profile.from_dict(profile or {})
    if prof.city_tier is None:
        prof.city_tier = 2
    if prof.has_gstin is None and prof.gstin_status is None:
        prof.has_gstin = False
    return prof, s


@router.post("/quote")
def quote(body: QuoteIn, db: Session = Depends(get_db)):
    prof, s = profile_for(db, body.session_id, body.profile)
    prof.term_months = 24 if body.term_months >= 24 else 12
    items = body.items or ({ln["product_id"]: ln["qty"] for ln in (s.bundle or {}).get("lines", [])} if s else {})
    b = price_custom(prof, items)
    d = b.to_dict()
    # add-ons: everything in the segment add-on list plus recommended items the owner switched off
    rec_lines = (s.bundle or {}).get("lines", []) if s else []
    switched_off = [ln for ln in rec_lines if ln["product_id"] not in items]
    d["switched_off"] = [{"product_id": ln["product_id"], "name": ln["name"], "qty": ln["qty"], "why": reason_text(ln, body.language)} for ln in switched_off]
    for ln in d["lines"]:
        orig = next((x for x in rec_lines if x["product_id"] == ln["product_id"]), None)
        ln["why"] = reason_text(orig or ln, body.language)
    for e in d["exclusions"]:
        e["why"] = rule_text(e["rule"], e["args"], e["name"], body.language)
    for a in d["addons"]:
        a["why"] = rule_text(a["rule"], a["args"], a["name"], body.language) if a["rule"] else ""
    d["business_type"], d["city"], d["partner_id"] = prof.business_type, prof.city, (s.partner_id if s else None)
    # both payment choices, computed by the one schedule function the order and payment use
    d["schedule_options"] = {"upfront": payplan.for_bundle(d, False), "emi": payplan.for_bundle(d, True)}
    d["current_spend"] = prof.current_spend
    return d


# ---- order ------------------------------------------------------------------------

class OrderIn(BaseModel):
    session_id: str | None = None
    profile: dict | None = None
    items: dict[str, int]
    term_months: int = 12
    setup_emi: bool = False
    phone: str
    business_name: str | None = None
    partner_id: str | None = None
    specimen: str | None = None


@router.post("/orders")
def place_order(body: OrderIn, db: Session = Depends(get_db), x_staff_token: str | None = Header(default=None)):
    if body.specimen and not get_settings().judge_mode:
        raise HTTPException(403, "specimen orders exist only in the judge demo")
    staff_claims = verify_staff(x_staff_token)
    phone = re.sub(r"[\s-]", "", body.phone)
    if not PHONE.match(phone):
        raise HTTPException(422, "Enter a 10-digit Indian mobile number")
    phone = phone[-10:]
    prof, s = profile_for(db, body.session_id, body.profile)
    tokens = (load_state(s).get("tokens") or {}) if s else {}
    gstin_token = tokens.get("gstin")
    spec = None
    if body.specimen:
        spec = kyc.specimens().get(body.specimen)
        if not spec:
            raise HTTPException(404, "unknown specimen")
        gstin_token = vault.tokenize(db, "gstin", spec["gstin"])
        reg = lookup_gstin(spec["gstin"]) or {}
        prof.gstin_status, prof.has_gstin, prof.legal_name, prof.gstin = reg.get("status"), True, reg.get("trade_name"), mask_gstin(spec["gstin"])
    try:
        order = create_order(db, prof, body.items, body.term_months, body.setup_emi, session_id=body.session_id,
                             phone_token=vault.tokenize(db, "phone", phone), gstin_token=gstin_token,
                             channel=(s.channel if s else "web"), partner_id=(staff_claims or {}).get("partner_id") or (s.partner_id if s else None),  # never from the request body
                             language=prof.language, specimen=body.specimen,
                             business_name=body.business_name or (spec or {}).get("business_name"))
    except ValueError as e:
        raise HTTPException(422, str(e))
    if spec and spec.get("udyam_number"):
        order.udyam_token = vault.tokenize(db, "udyam", spec["udyam_number"])
    if s:
        s.status = "ordered"
    verify = number_verify(phone)
    add_event(db, order, "number_verified", "Mobile number verified", method=verify["method"], masked=mask_phone(phone))
    db.commit()
    return {"order_id": order.id, "access_key": order.access_key, "phone_masked": mask_phone(phone), **public_view(order, _events(db, order))}


def _events(db: Session, order: Order) -> list[OrderEvent]:
    return list(db.scalars(select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.id)))


@router.get("/orders/{oid}")
def get_order(oid: str, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    return {**public_view(o, _events(db, o)), "consent": consent.current(db, o.id)}


# ---- consent ------------------------------------------------------------------------

@router.get("/consent/notice")
def notice():
    return {"version": consent.NOTICE_VERSION, "purposes": consent.PURPOSES}


class ConsentIn(BaseModel):
    choices: dict[str, bool]
    language: str = "en"
    channel: str = "web"


@router.post("/orders/{oid}/consent")
def give_consent(oid: str, body: ConsentIn, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    try:
        consent.record(db, o.id, body.choices, body.language, body.channel)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if o.status == "draft":
        o.status = "consented"
    add_event(db, o, "consent_given", "Consent recorded", purposes={k: bool(v) for k, v in body.choices.items()})
    db.commit()
    return consent.current(db, o.id)


@router.post("/orders/{oid}/consent/{purpose}/withdraw")
def withdraw_consent(oid: str, purpose: str, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    if purpose not in consent.PURPOSES:
        raise HTTPException(404, "unknown purpose")
    consent.withdraw(db, o.id, purpose)
    add_event(db, o, "consent_withdrawn", f"Consent withdrawn: {purpose.replace('_', ' ')}", purpose=purpose)
    db.commit()
    return consent.current(db, o.id)


# ---- KYC ------------------------------------------------------------------------

class GstinIn(BaseModel):
    gstin: str
    udyam_number: str | None = None


@router.post("/kyc/lookup")
def lookup(body: GstinIn):
    g = body.gstin.strip().upper()
    reg = lookup_gstin(g) if gstin_valid(g) else None
    return {"valid_format": gstin_valid(g), "found": bool(reg), "gstin_masked": mask_gstin(g),
            "registry": {k: reg[k] for k in ("legal_name", "trade_name", "constitution", "state", "status")} if reg else None}


@router.post("/orders/{oid}/kyc/identifiers")
def set_identifiers(oid: str, body: GstinIn, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    if not consent.has_consent(db, o.id, "kyc_verification"):
        raise HTTPException(403, "KYC needs your consent first")
    g = body.gstin.strip().upper()
    if not gstin_valid(g):
        raise HTTPException(422, "That is not a valid GSTIN (the check character does not match)")
    o.gstin_token = vault.tokenize(db, "gstin", g)
    if body.udyam_number:
        u = body.udyam_number.strip().upper()
        if not udyam_valid(u):
            raise HTTPException(422, "Udyam numbers look like UDYAM-MH-00-1234567")
        o.udyam_token = vault.tokenize(db, "udyam", u)
    o.status = "kyc_pending"
    db.commit()
    return lookup(GstinIn(gstin=g))


@router.post("/orders/{oid}/kyc/documents")
async def upload_document(oid: str, key: str = Query(...), doc_type: str = Form(...), file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "Photo too large (max 12 MB)")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "Upload a photo (JPG or PNG)")

    def work():
        db = SessionLocal()
        try:
            o = owner_order(db, oid, key)
            doc, ex = kyc.upload(db, o, doc_type, data, file.content_type or "image/png")
            if o.status in ("draft", "consented"):
                o.status = "kyc_pending"
            db.commit()
            return {"document_id": doc.id, "doc_type": doc_type, "quality": doc.quality, "fields": doc.fields}
        finally:
            db.close()

    try:
        return await run_in_threadpool(work)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


class SpecimenIn(BaseModel):
    specimen: str


@router.post("/orders/{oid}/kyc/specimen")
async def use_specimen(oid: str, body: SpecimenIn, key: str = Query(...)):
    """Judge/demo shortcut: upload the official specimen photos for applicant K01-K12."""
    files = kyc.specimen_files(body.specimen)
    if not files:
        raise HTTPException(404, "unknown specimen")

    def work():
        db = SessionLocal()
        try:
            o = owner_order(db, oid, key)
            spec = kyc.specimens()[body.specimen]
            if not o.gstin_token:
                o.gstin_token = vault.tokenize(db, "gstin", spec["gstin"])
            if spec.get("udyam_number") and not o.udyam_token:
                o.udyam_token = vault.tokenize(db, "udyam", spec["udyam_number"])
            o.specimen = body.specimen
            o.business_name = spec["business_name"]
            docs = []
            for dt, path in files.items():
                doc, _ = kyc.upload(db, o, dt, path.read_bytes(), "image/png")
                docs.append({"doc_type": dt, "quality": doc.quality, "fields": doc.fields})
            res = kyc.run(db, o)
            db.commit()
            return {"documents": docs, "result": res.to_dict(), "status": o.status}
        finally:
            db.close()

    try:
        return await run_in_threadpool(work)
    except PermissionError as e:
        raise HTTPException(403, str(e))


class DigiIn(BaseModel):
    udyam_number: str | None = None


@router.post("/orders/{oid}/kyc/digilocker")
def digilocker(oid: str, body: DigiIn, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    u = (body.udyam_number or "").strip().upper()
    if not u and o.udyam_token:
        u = vault.detokenize(db, o.udyam_token, "kyc_service", "kyc_verification", o.id)
    if not udyam_valid(u):
        raise HTTPException(422, "Enter your Udyam number to fetch the certificate")
    try:
        doc, _ = kyc.fetch_digilocker(db, o, u)
    except (LookupError, PermissionError) as e:
        raise HTTPException(404, str(e))
    o.udyam_token = vault.tokenize(db, "udyam", u)
    add_event(db, o, "digilocker", "Udyam certificate fetched from DigiLocker")
    db.commit()
    return {"document_id": doc.id, "fields": doc.fields, "source": "digilocker"}


@router.post("/orders/{oid}/kyc/evaluate")
async def evaluate(oid: str, key: str = Query(...)):
    def work():
        db = SessionLocal()
        try:
            o = owner_order(db, oid, key)
            res = kyc.run(db, o)
            db.commit()
            return {"result": res.to_dict(), "status": o.status}
        finally:
            db.close()

    try:
        return await run_in_threadpool(work)
    except PermissionError as e:
        raise HTTPException(403, str(e))


# ---- payment, booking, tracker --------------------------------------------------

PAY_METHODS = ("upi_autopay", "upi_once", "card", "netbanking", "pay_link")


class PayIn(BaseModel):
    method: str = "upi_autopay"
    upi_id: str | None = None


@router.post("/orders/{oid}/pay")
def pay(oid: str, body: PayIn, key: str = Query(...), idempotency_key: str | None = Header(None),
        db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    if o.payment and o.payment.get("status") == "captured":
        return o.payment  # a retry after a timeout never charges twice
    if o.status != "kyc_verified":
        raise HTTPException(409, "Payment opens once KYC is verified")
    if body.method not in PAY_METHODS:
        raise HTTPException(422, "Choose UPI Autopay, UPI, card, netbanking or a pay link")
    sched = o.bundle.get("schedule") or payplan.for_bundle(o.bundle, o.setup_emi)
    attempt = len([e for e in _events(db, o) if e.kind in ("payment_failed", "payment_done")]) + 1
    key_used = idempotency_key or f"{o.id}:{sched['hash']}:{attempt}"
    if body.upi_id and "fail" in body.upi_id:
        add_event(db, o, "payment_failed", "Payment did not go through", method=body.method, attempt=attempt)
        db.commit()
        raise HTTPException(402, "Payment failed. Nothing was charged. Try another UPI app or a card.")
    autopay = body.method in ("upi_autopay", "card")
    o.payment = {"status": "captured", "method": body.method, "amount_paise": sched["due_today"], "amount": sched["due_today"] / 100,
                 "schedule_hash": sched["hash"], "row": 0, "autopay_mandate": autopay,
                 "mandate_limit_paise": sched["mandate_limit"] if autopay else None,
                 "next_debit_paise": sched["rows"][1]["total"] if len(sched["rows"]) > 1 else None,
                 "idempotency_key": key_used, "reference": f"pay_{uuid.uuid4().hex[:14]}", "at": now().isoformat(),
                 "provider": "mock (Razorpay test mode adapter)"}
    o.status = "paid"
    add_event(db, o, "payment_done", "First payment received" + ("; Autopay set up" if autopay else ""),
              amount_paise=sched["due_today"], schedule_hash=sched["hash"])
    db.commit()
    return o.payment


@router.get("/orders/{oid}/slots")
def slots(oid: str, key: str = Query(...), db: Session = Depends(get_db)):
    return {"days": install_slots(owner_order(db, oid, key))}


class SlotIn(BaseModel):
    slot: str  # "2026-11-06 09:00-12:00"


def activation_block(db: Session, o: Order, product_id: str) -> str | None:
    """Why a product can't go live yet, or None. Checked at the moment of activation, not just at KYC."""
    from .care import SIM_PRODUCTS, sim_view
    if product_id in SIM_PRODUCTS:
        users = [u for u in sim_view(db, o)["users"] if u["product_id"] == product_id]
        needed = sum(ln["qty"] for ln in o.bundle.get("lines", []) if ln["product_id"] == product_id)
        if sum(u["status"] == "verified" for u in users) < needed:
            return "sim_kyc_pending"
    if store().products[product_id].requires_gstin and o.gstin_token:
        g = vault.detokenize(db, o.gstin_token, "kyc_service", "kyc_verification", o.id)
        reg = lookup_gstin(g) or {}
        if reg.get("status") != "Active":
            return f"gstin_{(reg.get('status') or 'missing').lower()}"
    return None


HOLD_TEXT = {"sim_kyc_pending": "Waiting for each SIM user to verify (a link was sent to them)",
             "gstin_cancelled": "On hold: the GST registry now shows the GSTIN as Cancelled",
             "gstin_suspended": "On hold: the GST registry now shows the GSTIN as Suspended"}


def _hold(db: Session, o: Order, product_id: str, reason: str) -> None:
    already = any(e.kind == "activation_hold" and e.product_id == product_id and e.detail.get("reason") == reason for e in _events(db, o))
    if not already:
        add_event(db, o, "activation_hold", HOLD_TEXT.get(reason, f"On hold: {reason}"), product_id, reason=reason)


@router.post("/orders/{oid}/schedule")
def schedule(oid: str, body: SlotIn, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    if o.status not in ("paid", "scheduled"):
        raise HTTPException(409, "Book installation after payment")
    offered = {f"{d['date']} {s}" for d in install_slots(o) for s in d["slots"]}
    if body.slot not in offered:
        raise HTTPException(422, "Pick one of the offered installation slots")
    o.install_slot = body.slot
    o.status = "scheduled"
    add_event(db, o, "install_scheduled", f"Installation booked for {body.slot}", slot=body.slot)
    for ln in [ln for ln in o.bundle["lines"] if ln["install_days"] <= 1]:  # cloud services and SIMs need no visit
        reason = activation_block(db, o, ln["product_id"])
        if reason:
            _hold(db, o, ln["product_id"], reason)
        else:
            add_event(db, o, "product_active", f"{ln['name']} is live", ln["product_id"])
    db.flush()
    complete_if_all_live(db, o)
    db.commit()
    return public_view(o, _events(db, o))


@router.post("/orders/{oid}/advance")
def advance_order(oid: str, key: str = Query(...), db: Session = Depends(get_db)):
    """Demo control standing in for field ops: complete the next product that is allowed to go live."""
    if not get_settings().judge_mode:
        raise HTTPException(403, "demo controls are off")
    o = owner_order(db, oid, key)
    if o.status not in ("scheduled", "active"):
        raise HTTPException(409, "Book installation first")
    ev = advance(db, o, lambda pid: activation_block(db, o, pid), lambda pid, r: _hold(db, o, pid, r))
    db.flush()
    complete_if_all_live(db, o)
    db.commit()
    return public_view(o, _events(db, o)) | {"advanced": ev.title if ev else None}


@router.get("/orders/{oid}/stream")
async def stream(oid: str, request: Request, key: str = Query(...)):
    db = SessionLocal()
    try:
        owner_order(db, oid, key)
    finally:
        db.close()
    q = bus.subscribe(oid)

    async def gen():
        try:
            yield {"event": "hello", "data": json.dumps({"order": oid})}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                    yield {"event": "order", "data": json.dumps(ev, default=str)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            bus.unsubscribe(oid, q)

    return EventSourceResponse(gen())


# ---- data principal rights ----------------------------------------------------------

@router.get("/orders/{oid}/my-data")
def my_data(oid: str, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    out = {"order": public_view(o, _events(db, o)), "consents": consent.current(db, o.id), "identifiers": {}}
    for kind, tok in (("gstin", o.gstin_token), ("udyam", o.udyam_token), ("phone", o.phone_token)):
        if tok:
            try:
                out["identifiers"][kind] = vault.detokenize(db, tok, "owner", "rights_access", o.id)
            except Exception:  # noqa: BLE001 - shredded
                out["identifiers"][kind] = None
    docs = db.scalars(select(Document).where(Document.order_id == o.id)).all()
    out["documents"] = [{"type": d.doc_type, "uploaded": d.created_at.isoformat(), "delete_after": d.delete_after.isoformat() if d.delete_after else None,
                         "deleted": d.deleted_at is not None, "fields": d.fields} for d in docs]
    db.commit()
    return out


@router.post("/orders/{oid}/erase")
def erase(oid: str, key: str = Query(...), db: Session = Depends(get_db)):
    o = owner_order(db, oid, key)
    for d in db.scalars(select(Document).where(Document.order_id == o.id, Document.deleted_at.is_(None))).all():
        shred_document(db, d, "owner_erasure")
    for tok in (o.gstin_token, o.udyam_token, o.phone_token):
        if tok:
            vault.shred(db, tok)
    o.status = "cancelled" if o.status != "active" else o.status
    o.business_name, o.profile, o.kyc_result = "(erased)", {}, None
    db.add(AuditLog(actor="owner", action="erasure", target=o.id, purpose="rights_access", detail={}))
    add_event(db, o, "erased", "Your personal data was erased")
    db.commit()
    return {"erased": True}
