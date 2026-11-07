"""Smart KYC orchestration: consent gate, encrypted storage, extraction, decision, events."""
from __future__ import annotations

import json
import pickle
import threading
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import ROOT, get_settings
from ..data_store import lookup_udyam, store
from ..db import Approval, Document, Order
from ..network.telco import sim_swap
from ..orders.service import add_event
from ..privacy import vault
from ..privacy.consent import has_consent
from ..privacy.crypto import sha256
from ..privacy.storage import read_document, save_document
from .checks import DOC_TYPES, ROUTES, Check, Declared, Result, evaluate
from . import vision
from .messages import local_fix
from .ocr import Extraction, Quality, decode, extract

_cache: dict[str, Extraction] = {}
_lock = threading.Lock()


def _known():
    ds = store()
    return set(ds.gstin), set(ds.udyam)


def read(data: bytes, doc_type: str) -> Extraction:
    key = f"{doc_type}:{sha256(data)}"
    with _lock:
        hit = _cache.get(key)
    if hit:
        return hit
    kg, ku = _known()
    ex = extract(decode(data), doc_type, kg, ku)
    with _lock:
        _cache[key] = ex
    return ex


def specimens() -> dict:
    return json.loads((get_settings().data_dir / "specimens.json").read_text())


# Our own demo applicants, kept apart from the official pack (and from its expected outcomes).
# K02R: K02's clinic in a rented unit, the bill in the landlord's name; a rent agreement is held back
# so the demo can show both ways out (landlord e-sign, or uploading the agreement).
EXTRA = {"K02R": {"base": "K02", "landlord": "Sunita Banerjee", "held_back": ["rent_agreement"]}}


def specimen(k: str) -> dict | None:
    if k in EXTRA:
        return {**specimens()[EXTRA[k]["base"]], **EXTRA[k]}
    return specimens().get(k)


def specimen_files(k: str) -> dict[str, Path]:
    if k in EXTRA:
        extra = get_settings().data_dir / "demo_extra"
        own = {dt: extra / f"{k}_{dt}.png" for dt in DOC_TYPES if (extra / f"{k}_{dt}.png").exists()}
        return {**specimen_files(EXTRA[k]["base"]), **own}
    d = get_settings().data_dir / "kyc_documents"
    return {dt: d / f"{k}_{dt}.png" for dt in DOC_TYPES if (d / f"{k}_{dt}.png").exists()}


BAKED = ROOT / "var" / "specimen_reads.pkl"  # written at image build (Dockerfile), never at runtime


def warm_cache() -> None:
    """Pre-read the 47 specimen images so the live demo answers instantly.
    The container image carries these reads, so a new instance never spends its first minutes on OCR."""
    if BAKED.exists():
        with _lock:
            _cache.update(pickle.loads(BAKED.read_bytes()))
        return
    for k in [*specimens(), *EXTRA]:
        for dt, path in specimen_files(k).items():
            try:
                read(path.read_bytes(), dt)
            except Exception:  # noqa: BLE001
                pass


def bake() -> None:
    warm_cache()
    BAKED.parent.mkdir(parents=True, exist_ok=True)
    BAKED.write_bytes(pickle.dumps(dict(_cache)))
    print(f"baked {len(_cache)} specimen reads")


def require_consent(db: Session, order: Order) -> None:
    if not has_consent(db, order.id, "kyc_verification"):
        raise PermissionError("KYC needs your consent first")


def upload(db: Session, order: Order, doc_type: str, data: bytes, mime: str) -> tuple[Document, Extraction]:
    require_consent(db, order)
    if doc_type not in DOC_TYPES:
        raise ValueError("unknown document type")
    doc = save_document(db, order.id, doc_type, data, mime)
    ex = read(data, doc_type)
    if vision.enabled() and has_consent(db, order.id, "ai_document_reading") and doc_type in vision.BUSINESS_DOCS:
        ex = vision.merge(ex, vision.read(data, mime, doc_type), doc_type)  # second reader, consented, business documents only
        with _lock:
            _cache[f"{doc_type}:{sha256(data)}"] = ex
    doc.quality = {"sharpness": ex.quality.sharpness, "skew_deg": ex.quality.skew_deg, "blurred": ex.quality.blurred,
                   "faint": ex.quality.faint, "detected": ex.doc_type_detected}
    doc.fields = _masked(ex.fields)
    return doc, ex


def _masked(fields: dict) -> dict:
    from .ids import gstin_valid, mask_gstin, mask_udyam
    out = dict(fields)
    if out.get("gstin"):
        out["gstin"] = mask_gstin(out["gstin"]) if gstin_valid(out["gstin"]) else out["gstin"][:4] + "*******"
    if out.get("udyam_number"):
        out["udyam_number"] = mask_udyam(out["udyam_number"])
    if out.get("id_no"):
        out["id_no"] = out["id_no"][:7] + "****" + out["id_no"][-2:]
    if out.get("consumer_no"):
        out["consumer_no"] = "******" + out["consumer_no"][-4:]
    return out


def fetch_digilocker(db: Session, order: Order, udyam_number: str) -> tuple[Document, Extraction]:
    """Mock DigiLocker pull: Udyam certificates from DigiLocker are officially recognised
    (Ministry of MSME circular, 1 January 2025). Returns the registry record as the document."""
    require_consent(db, order)
    rec = lookup_udyam(udyam_number)
    if not rec:
        raise LookupError("No Udyam certificate found in DigiLocker for that number")
    fields = {"udyam_number": rec["udyam_number"], "enterprise_name": rec["enterprise_name"], "major_activity": rec["major_activity"],
              "city": rec["city"], "state": rec["state"], "date_of_registration": rec["date_of_registration"]}
    data = json.dumps({"source": "DigiLocker (mock)", **fields}).encode()
    doc = save_document(db, order.id, "udyam_certificate", data, "application/json")
    ex = Extraction("udyam_certificate", Quality(1e5, 0.02, 0.0, False, False), fields, {"udyam_number": {"healed": False, "source": "digilocker"}})
    with _lock:
        _cache[f"udyam_certificate:{sha256(data)}"] = ex
    doc.fields, doc.quality = _masked(fields), {"source": "digilocker"}
    return doc, ex


def latest_docs(db: Session, order: Order) -> dict[str, Extraction | None]:
    docs: dict[str, Extraction | None] = {dt: None for dt in DOC_TYPES}
    rows = db.scalars(select(Document).where(Document.order_id == order.id, Document.deleted_at.is_(None)).order_by(Document.created_at)).all()
    for doc in rows:
        data = read_document(db, doc, "kyc_service")
        key = f"{doc.doc_type}:{sha256(data)}"
        with _lock:
            ex = _cache.get(key)
        if ex is None:
            ex = read(data, doc.doc_type) if doc.mime.startswith("image/") else None
        if ex is not None:
            docs[doc.doc_type] = ex
    return docs


def route_of(order: Order) -> str:
    """The proof route the owner chose; otherwise inferred from what they declared."""
    chosen = (order.profile or {}).get("kyc_route")
    if chosen in ROUTES:
        return chosen
    if order.gstin_token:
        return "gst"
    return "udyam" if order.udyam_token else "shop_licence"


def landlord_signed(db: Session, order: Order) -> str | None:
    """The name the landlord e-signed with, once they confirmed the shop is let to this business."""
    a = db.scalar(select(Approval).where(Approval.order_id == order.id, Approval.kind == "landlord", Approval.status == "approved")
                  .order_by(Approval.decided_at.desc()))
    return vault.detokenize(db, a.name_token, "kyc_service", "kyc_verification", order.id) if a and a.name_token else None


def run(db: Session, order: Order, declared_udyam: str | None = None) -> Result:
    require_consent(db, order)
    route = route_of(order)
    gstin = vault.detokenize(db, order.gstin_token, "kyc_service", "kyc_verification", order.id) if order.gstin_token and route == "gst" else None
    udyam = declared_udyam
    if not udyam and order.udyam_token:
        udyam = vault.detokenize(db, order.udyam_token, "kyc_service", "kyc_verification", order.id)
    result = evaluate(Declared(gstin, udyam, order.business_name, route, landlord_signed(db, order)), latest_docs(db, order))
    # without a verified GSTIN, GST-only products cannot be sold: the owner removes them or switches route
    if route != "gst":
        gst_only = [ln["name"] for ln in order.bundle.get("lines", []) if store().products[ln["product_id"]].requires_gstin]
        if gst_only:
            result.checks.append(Check("bundle.gst_only", "hard", "fail", "fix", f"These need a GSTIN: {', '.join(gst_only)}.",
                                       "Remove them from the order, or verify with your GSTIN.", {"products": gst_only}))
            if result.outcome == "verified":
                result.outcome = "fix_needed"
    # telco-native fraud signal: a SIM swapped in the last 72 hours blocks auto-approval
    if order.phone_token:
        phone = vault.detokenize(db, order.phone_token, "kyc_service", "kyc_verification", order.id)
        sw = sim_swap(phone)
        if sw["swapped_recently"]:
            result.checks.append(Check("signatory.sim_swap", "hard", "fail", "review", "This mobile number's SIM was changed in the last 72 hours.",
                                       "A partner will confirm by video call.", sw))
            result.outcome = "review"
        else:
            result.checks.append(Check("signatory.sim_swap", "hard", "pass", "review", "No recent SIM swap on the signatory's number."))
    # GST-only products need an Active GSTIN even after KYC
    reg = result.registry.get("gstin")
    if reg and reg["status"] != "Active":
        gst_only = [ln["name"] for ln in order.bundle.get("lines", []) if store().products[ln["product_id"]].requires_gstin]
        if gst_only:
            result.checks.append(Check("bundle.gst_only", "hard", "fail", "review", f"These need an active GSTIN and cannot be activated: {', '.join(gst_only)}.",
                                       "Remove them, or reactivate the GSTIN.", {"products": gst_only}))
    for c in result.checks:  # what the owner reads: one instruction, in their language
        if c.status == "fail":
            c.args = {**c.args, "local_fix": local_fix(c.id, c.severity, c.args, order.language)}
    order.kyc_result = result.to_dict()
    order.kyc_outcome = result.outcome
    if result.outcome == "verified":
        order.status = "kyc_verified"
        add_event(db, order, "kyc_verified", "KYC verified automatically")
    elif result.outcome == "fix_needed":
        order.status = "kyc_fix"
        add_event(db, order, "kyc_fix", "KYC needs a quick fix from you",
                  fixes=[c.fix for c in result.checks if c.status == "fail" and c.fix])
    else:
        order.status = "kyc_review"
        add_event(db, order, "kyc_review", "KYC is with our team for a quick check")
    db.flush()
    return result
