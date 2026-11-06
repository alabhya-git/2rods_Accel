"""Trust fixes from the evaluations: fail-closed KYC, no-GST routes, real help, locked demo controls."""
import hashlib
import hmac
import json

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.config import get_settings
from app.kyc.checks import Declared, evaluate
from app.kyc.ocr import Extraction, Quality
from app.main import app

GOOD = Quality(20000.0, 0.05, 0.0, False, False)
K09 = "37LDYXK0296F1ZB"


def staff_headers(c, user, secret):
    return {"Authorization": "Bearer " + c.post("/api/staff/login", json={"user": user, "secret": secret}).json()["token"]}


def photo(text: str) -> bytes:
    """A sharp, readable photo that is not a KYC document (like an app screenshot)."""
    img = np.full((900, 700, 3), 255, np.uint8)
    for i, line in enumerate(text.split("\n")):
        cv2.putText(img, line, (40, 120 + 70 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (20, 20, 20), 2)
    return cv2.imencode(".png", img)[1].tobytes()


# ---- fail-closed KYC ---------------------------------------------------------------------

def test_unrecognised_pages_with_no_fields_are_never_verified():
    docs = {dt: Extraction(None, GOOD, {}) for dt in ("gst_certificate", "address_proof", "signatory_id")}
    r = evaluate(Declared(K09, None, "Anything"), docs)
    assert r.outcome != "verified"
    assert {"gst_certificate.type", "address_proof.type", "signatory_id.type"} <= {c.id for c in r.checks if c.status == "fail"}


def test_right_type_but_missing_fields_needs_a_fix():
    docs = {"gst_certificate": Extraction("gst_certificate", GOOD, {"gstin": K09}),
            "address_proof": Extraction("address_proof", GOOD, {"bill_date": "2026-07-01"}),
            "signatory_id": Extraction("signatory_id", GOOD, {"name": "X"})}
    r = evaluate(Declared(K09, None, "Anything"), docs)
    assert r.outcome != "verified"
    assert {"gst_certificate.fields", "address_proof.fields", "signatory_id.fields"} <= {c.id for c in r.checks if c.status == "fail"}


def test_future_bill_date_goes_to_a_person():
    docs = {"gst_certificate": None, "address_proof": Extraction("address_proof", GOOD, {"bill_date": "2027-01-01", "billed_to": "A", "supply_address": "B - 123456"}),
            "signatory_id": None}
    r = evaluate(Declared(K09, None, "A"), docs)
    assert "address_proof.future" in {c.id for c in r.checks if c.status == "fail"}


def test_four_screenshots_through_the_real_upload_and_ocr_are_rejected():
    """The evaluations' end-to-end probe: unrelated clear images plus an Active GSTIN."""
    with TestClient(app) as c:
        o = c.post("/api/orders", json={"profile": {"segment": "prof", "employees": 5, "city": "Pune", "city_tier": 1, "has_gstin": True, "gstin_status": "Active"},
                                        "items": {"P02": 1}, "phone": "9812345670"}).json()
        oid, key = o["order_id"], o["access_key"]
        c.post(f"/api/orders/{oid}/consent?key={key}", json={"choices": {"kyc_verification": True, "service_delivery": True}})
        c.post(f"/api/orders/{oid}/kyc/identifiers?key={key}", json={"gstin": K09})
        for dt in ("gst_certificate", "udyam_certificate", "address_proof", "signatory_id"):
            files = {"file": (f"{dt}.png", photo(f"Accel Business\nYour order\nTrack status\n{dt}"), "image/png")}
            assert c.post(f"/api/orders/{oid}/kyc/documents?key={key}", data={"doc_type": dt}, files=files).status_code == 200
        res = c.post(f"/api/orders/{oid}/kyc/evaluate?key={key}").json()["result"]
        assert res["outcome"] != "verified"
        # and the owner reads a fix, not an English error, in their language
        assert all(ch["args"].get("local_fix") for ch in res["checks"] if ch["status"] == "fail")


# ---- no-GST routes ---------------------------------------------------------------------------

def _order(c, items, phone):
    o = c.post("/api/orders", json={"profile": {"segment": "prof", "business_type": "Insurance agency", "employees": 25,
                                                "city": "Visakhapatnam", "city_tier": 2, "has_gstin": False},
                                    "items": items, "phone": phone, "language": "hi"}).json()
    oid, key = o["order_id"], o["access_key"]
    c.post(f"/api/orders/{oid}/consent?key={key}", json={"choices": {"kyc_verification": True, "service_delivery": True}})
    return oid, key


def _upload(c, oid, key, spec, dts):
    from app.kyc.service import specimen_files
    for dt, path in specimen_files(spec).items():
        if dt in dts:
            c.post(f"/api/orders/{oid}/kyc/documents?key={key}", data={"doc_type": dt}, files={"file": (path.name, path.read_bytes(), "image/png")})


def test_udyam_route_verifies_without_any_gst_document():
    from app.kyc.service import specimens
    with TestClient(app) as c:
        oid, key = _order(c, {"P02": 1, "P16": 5}, "9811100001")
        r = c.post(f"/api/orders/{oid}/kyc/route?key={key}", json={"route": "udyam"}).json()
        assert "gst_certificate" not in r["needs"] and r["gst_only_products"] == []
        assert c.post(f"/api/orders/{oid}/kyc/digilocker?key={key}", json={"udyam_number": specimens()["K09"]["udyam_number"]}).status_code == 200
        _upload(c, oid, key, "K09", ("address_proof", "signatory_id"))
        res = c.post(f"/api/orders/{oid}/kyc/evaluate?key={key}").json()["result"]
        assert res["route"] == "udyam"
        assert res["outcome"] == "verified", [x for x in res["checks"] if x["status"] == "fail"]


def test_gst_only_products_are_refused_on_a_non_gst_route():
    from app.kyc.service import specimens
    with TestClient(app) as c:
        o = c.post("/api/orders", json={"profile": {"segment": "prof", "employees": 25, "city": "Visakhapatnam", "city_tier": 2, "has_gstin": True,
                                                    "gstin_status": "Declared"},
                                        "items": {"P02": 1, "P15": 1}, "phone": "9811100002"}).json()
        oid, key = o["order_id"], o["access_key"]
        c.post(f"/api/orders/{oid}/consent?key={key}", json={"choices": {"kyc_verification": True, "service_delivery": True}})
        assert c.post(f"/api/orders/{oid}/kyc/route?key={key}", json={"route": "udyam"}).json()["gst_only_products"]
        c.post(f"/api/orders/{oid}/kyc/digilocker?key={key}", json={"udyam_number": specimens()["K09"]["udyam_number"]})
        _upload(c, oid, key, "K09", ("address_proof", "signatory_id"))
        res = c.post(f"/api/orders/{oid}/kyc/evaluate?key={key}").json()["result"]
        assert res["outcome"] == "fix_needed" and "bundle.gst_only" in {x["id"] for x in res["checks"] if x["status"] == "fail"}


def test_shop_licence_route_always_reaches_a_person():
    r = evaluate(Declared(None, None, "A", "shop_licence"),
                 {"shop_licence": Extraction("shop_licence", GOOD, {}, text="Shops and Establishments Registration Certificate " * 3),
                  "address_proof": None, "signatory_id": None})
    assert r.route == "shop_licence" and "shop_licence.review" in {c.id for c in r.checks if c.status == "fail"}


# ---- talk to a person ---------------------------------------------------------------------------

def test_talk_to_a_person_creates_a_task_partners_can_see_and_act_on():
    with TestClient(app) as c:
        sid = c.post("/api/advisor/sessions", json={"language": "ta"}).json()["session_id"]
        c.post(f"/api/advisor/sessions/{sid}/messages", json={"text": "சென்னையில் என் கடை, 4 பேர் வேலை செய்கிறார்கள்"})
        h = c.post("/api/help", json={"phone": "98400 12345", "window": "today_evening", "language": "ta", "session_id": sid,
                                      "reason": "prefer_person"}).json()
        assert h["status"] == "open" and "45" in h["phone_masked"] and "12345" not in h["phone_masked"]
        p = staff_headers(c, "PARTNER-001", "partner-demo")
        queue = c.get("/api/backoffice/help", headers=p).json()
        task = next(t for t in queue if t["id"] == h["id"])
        assert task["language"] == "ta" and task["summary"]["employees"] == 4 and "98400" not in json.dumps(task)
        assert c.post(f"/api/backoffice/help/{h['id']}", headers=p, json={"status": "assigned"}).json()["assignee"] == "Sharma Telecom, Jaipur"
        assert c.get(f"/api/help/{h['id']}").json()["status"] == "assigned"


# ---- demo controls and production -----------------------------------------------------------------

def test_reset_needs_an_admin():
    with TestClient(app) as c:
        assert c.post("/api/judge/reset").status_code == 401
        assert c.post("/api/judge/reset", headers=staff_headers(c, "reviewer-1", "review-demo")).status_code == 403


def test_production_refuses_demo_settings(monkeypatch):
    from app.security import production_problems
    st = get_settings()
    monkeypatch.setattr(st, "environment", "prod")
    problems = " ".join(production_problems())
    for needle in ("JUDGE_MODE", "STAFF_ACCOUNTS", "CORS_ORIGINS", "MOCK_ADAPTERS"):
        assert needle in problems


def test_whatsapp_webhook_checks_signature_and_ignores_retries(monkeypatch):
    st = get_settings()
    monkeypatch.setattr(st, "whatsapp_app_secret", "s3cret")
    body = json.dumps({"entry": [{"changes": [{"value": {"messages": [
        {"id": "wamid.TEST1", "from": "919800000077", "type": "text", "text": {"body": "Salon in Pune, 2 staff, no GST"}}]}}]}]}).encode()
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    with TestClient(app) as c:
        assert c.post("/api/whatsapp/webhook", content=body, headers={"x-hub-signature-256": "sha256=bad"}).status_code == 401
        assert c.post("/api/whatsapp/webhook", content=body, headers={"x-hub-signature-256": sig}).json() == {"ok": True}
        assert c.post("/api/whatsapp/webhook", content=body, headers={"x-hub-signature-256": sig}).json().get("duplicate")


def test_whatsapp_remembers_a_returning_owner():
    with TestClient(app) as c:
        a = c.post("/api/whatsapp/simulate", json={"from_number": "9800000088", "text": "I have a bakery"}).json()
        b = c.post("/api/whatsapp/simulate", json={"from_number": "9800000088", "text": "3 staff"}).json()
        assert a["session_id"] == b["session_id"]
