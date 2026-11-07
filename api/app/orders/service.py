"""Quote -> order -> consent -> KYC -> payment -> installation -> live."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..data_store import store
from ..db import AuditLog, Order, OrderEvent, aware, now
from ..engine import schedule
from ..engine.profile import Profile
from ..engine.recommend import price_custom
from ..kyc.ids import mask_gstin, mask_phone
from .events import after_commit, bus

STATUS_FLOW = ["draft", "consented", "kyc_pending", "kyc_fix", "kyc_review", "kyc_verified", "paid", "scheduled", "active", "cancelled"]


def add_event(db: Session, order: Order, kind: str, title: str, product_id: str | None = None, **detail) -> OrderEvent:
    ev = OrderEvent(order_id=order.id, kind=kind, title=title, product_id=product_id, detail=detail)
    db.add(ev)
    db.flush()
    # announced only after the commit: a step that rolls back is never shown to the owner
    after_commit(db, order.id, {"id": ev.id, "ts": ev.ts.isoformat(), "kind": kind, "title": title, "product_id": product_id, "detail": detail})
    return ev


def create_order(db: Session, profile: Profile, items: dict[str, int], term_months: int, setup_emi: bool, *,
                 session_id: str | None, phone_token: str | None, gstin_token: str | None, channel: str,
                 partner_id: str | None, language: str, specimen: str | None = None, business_name: str | None = None) -> Order:
    profile.term_months = 24 if term_months >= 24 else 12
    bundle = price_custom(profile, items)  # priced again on the server; client numbers are never trusted
    if not bundle.lines:
        raise ValueError("nothing eligible to order")
    bd = bundle.to_dict()
    bd["schedule"] = schedule.for_bundle(bd, setup_emi)  # every later amount is read from this
    order = Order(session_id=session_id, status="draft", business_name=business_name or profile.legal_name or profile.business_type,
                  segment=profile.segment, city=profile.city, language=language, channel=channel, partner_id=partner_id,
                  profile=profile.to_dict(), bundle=bd, term_months=profile.term_months, monthly=bundle.monthly,
                  setup=bundle.setup, setup_emi=setup_emi, phone_token=phone_token, gstin_token=gstin_token, specimen=specimen)
    db.add(order)
    db.flush()
    add_event(db, order, "order_placed", "Order placed", monthly=bundle.monthly, products=[ln.name for ln in bundle.lines])
    db.add(AuditLog(actor="owner" if not partner_id else f"partner:{partner_id}", action="order_created", target=order.id, purpose="service_delivery", detail={}))
    return order


def milestones(order: Order, events: list[OrderEvent]) -> list[dict]:
    """The tracker timeline: journey steps, then one row per product with its ETA."""
    kinds = {e.kind: e for e in events}
    steps = [("order_placed", "Order placed"), ("consent_given", "Consent recorded"), ("kyc_verified", "KYC verified"),
             ("payment_done", "First payment and Autopay"), ("install_scheduled", "Installation booked")]
    if any(e.kind == "approval_requested" and e.detail.get("who") == "owner" for e in events):
        steps.insert(3, ("owner_approved", "Owner approved"))  # staff placed it: the owner's yes comes before any charge
    out = []
    for kind, title in steps:
        e = kinds.get(kind)
        if kind == "owner_approved" and not e and kinds.get("owner_declined"):
            out.append({"kind": kind, "title": kinds["owner_declined"].title, "status": "attention", "at": kinds["owner_declined"].ts.isoformat()})
            continue
        if kind == "kyc_verified" and not e:
            alt = kinds.get("kyc_review") or kinds.get("kyc_fix")
            if alt:
                out.append({"kind": alt.kind, "title": alt.title, "status": "attention", "at": alt.ts.isoformat()})
                continue
        out.append({"kind": kind, "title": title, "status": "done" if e else "pending", "at": e.ts.isoformat() if e else None})
    base = kinds.get("payment_done")
    start = aware(base.ts) if base else None
    slot_day = _slot_date(order.install_slot)
    activated = {e.product_id: e for e in events if e.kind == "product_active"}
    for ln in order.bundle.get("lines", []):
        eta = None
        if start:
            eta_dt = start + timedelta(days=ln["install_days"])
            if slot_day and ln["product_id"] in ("P01", "P02", "P03", "P04", "P05", "P06", "P22", "P23", "P09"):
                eta_dt = max(eta_dt, datetime.combine(slot_day, datetime.min.time(), tzinfo=timezone.utc))
            eta = eta_dt.date().isoformat()
        a = activated.get(ln["product_id"])
        out.append({"kind": "product", "product_id": ln["product_id"], "title": f"{ln['name']}" + (f" x{ln['qty']}" if ln["qty"] > 1 else ""),
                    "status": "done" if a else ("pending" if not start else "in_progress"), "eta": eta,
                    "install_days": ln["install_days"], "at": a.ts.isoformat() if a else None})
    return out


def _slot_date(slot: str | None) -> date | None:
    if not slot:
        return None
    try:
        return date.fromisoformat(slot[:10])
    except ValueError:
        return None


def install_slots(order: Order) -> list[dict]:
    first = now().date() + timedelta(days=1)
    days = []
    for i in range(7):
        d = first + timedelta(days=i)
        if d.weekday() == 6:
            continue
        days.append({"date": d.isoformat(), "slots": ["09:00-12:00", "12:00-15:00", "15:00-18:00"]})
    return days


def complete_if_all_live(db: Session, order: Order) -> bool:
    """However products went live (same-day at booking, or by field ops), the order completes once all are."""
    live = {e.product_id for e in db.scalars(select(OrderEvent).where(OrderEvent.order_id == order.id, OrderEvent.kind == "product_active"))}
    if order.status != "active" and all(ln["product_id"] in live for ln in order.bundle.get("lines", [])):
        order.status = "active"
        add_event(db, order, "order_active", "Everything is live. Welcome to Accel Business!")
        return True
    return False


def advance(db: Session, order: Order, blocked=lambda pid: None, hold=lambda pid, reason: None) -> OrderEvent | None:
    """Demo control: complete the next pending product (as field ops would), unless it is blocked."""
    events = list(db.scalars(select(OrderEvent).where(OrderEvent.order_id == order.id)))
    done = {e.product_id for e in events if e.kind == "product_active"}
    for ln in sorted(order.bundle.get("lines", []), key=lambda ln: ln["install_days"]):
        if ln["product_id"] not in done:
            reason = blocked(ln["product_id"])
            if reason:
                hold(ln["product_id"], reason)
                continue
            ev = add_event(db, order, "product_active", f"{ln['name']} is live", ln["product_id"])
            remaining = [x for x in order.bundle["lines"] if x["product_id"] not in done | {ln["product_id"]}]
            if not remaining:
                order.status = "active"
                add_event(db, order, "order_active", "Everything is live. Welcome to Accel Business!")
            return ev
    return None


def public_view(order: Order, events: list[OrderEvent]) -> dict:
    return {
        "id": order.id, "status": order.status, "business_name": order.business_name, "segment": order.segment, "city": order.city,
        "language": order.language, "channel": order.channel, "partner_id": order.partner_id, "created_at": order.created_at.isoformat(),
        "bundle": order.bundle, "term_months": order.term_months, "monthly": order.monthly, "setup": order.setup, "setup_emi": order.setup_emi,
        "kyc_outcome": order.kyc_outcome, "kyc": order.kyc_result, "payment": order.payment, "install_slot": order.install_slot,
        "gstin_masked": (order.profile or {}).get("gstin"), "specimen": order.specimen,
        "customer": (order.profile or {}).get("accel_account"), "placed_by": (order.profile or {}).get("placed_by", "owner"),
        "milestones": milestones(order, events),
        "events": [{"id": e.id, "ts": e.ts.isoformat(), "kind": e.kind, "title": e.title, "product_id": e.product_id, "detail": e.detail} for e in events],
    }
