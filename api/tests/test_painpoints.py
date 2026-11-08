"""The hidden pain points: the owner isn't the one ordering, the shop is rented, the customer is
already with Dukaan Connect, scam calls, and products that are live but never set up."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data_store import store
from app.kyc import service as kyc
from app.kyc.checks import DOC_TYPES, Declared, evaluate
from app.kyc.ocr import decode, extract
from app.main import app

CONSENT = {"choices": {"kyc_verification": True, "service_delivery": True, "order_updates": True}}


def staff_headers(c, user, secret):
    return {"Authorization": "Bearer " + c.post("/api/staff/login", json={"user": user, "secret": secret}).json()["token"]}


def order(c, items, phone, **extra):
    o = c.post("/api/orders", json={"profile": {"city": "Jaipur", "employees": 5, "has_gstin": True, "gstin_status": "Active"},
                                    "items": items, "term_months": 12, "phone": phone, **extra})
    assert o.status_code == 200, o.text
    o = o.json()
    return o, o["order_id"], o["access_key"]


def kyc_ok(c, oid, key, specimen="K09"):
    assert c.post(f"/api/orders/{oid}/consent?key={key}", json=CONSENT).status_code == 200
    return c.post(f"/api/orders/{oid}/kyc/specimen?key={key}", json={"specimen": specimen}).json()


def book(c, oid, key):
    day = c.get(f"/api/orders/{oid}/slots?key={key}").json()["days"][0]
    return c.post(f"/api/orders/{oid}/schedule?key={key}", json={"slot": f"{day['date']} {day['slots'][0]}"}).json()


# ---- rented shop: the bill is in the landlord's name ------------------------------------------

@pytest.fixture(scope="module")
def k02r():
    ds, spec = store(), kyc.specimen("K02R")
    docs = {dt: None for dt in DOC_TYPES}
    for dt, path in kyc.specimen_files("K02R").items():
        docs[dt] = extract(decode(path.read_bytes()), dt, set(ds.gstin), set(ds.udyam))
    return spec, docs


def failed(r):
    return {c.id for c in r.checks if c.level == "hard" and c.status == "fail"}


def test_rented_shop_without_proof_is_a_fix_the_owner_can_make(k02r):
    spec, docs = k02r
    r = evaluate(Declared(spec["gstin"], spec["udyam_number"], spec["business_name"]), {**docs, "rent_agreement": None})
    assert r.outcome == "fix_needed" and failed(r) == {"address_proof.name"}
    c = next(c for c in r.checks if c.id == "address_proof.name")
    assert c.severity == "fix" and c.args["billed_to"] == "Sunita Banerjee"


def test_rent_agreement_links_the_landlords_bill_to_the_business(k02r):
    spec, docs = k02r
    r = evaluate(Declared(spec["gstin"], spec["udyam_number"], spec["business_name"]), docs)
    assert r.outcome == "verified", failed(r)
    assert any(c.id == "address_proof.name" and c.args.get("via") == "rent_agreement" for c in r.checks)


def test_rent_agreement_for_someone_else_goes_to_a_person(k02r):
    spec, docs = k02r
    lease = docs["rent_agreement"]
    other = type(lease)(lease.doc_type_detected, lease.quality, {**lease.fields, "landlord": "Ramesh Gupta", "tenant": "Kaveri Stays LLP"})
    r = evaluate(Declared(spec["gstin"], spec["udyam_number"], spec["business_name"]), {**docs, "rent_agreement": other})
    assert r.outcome == "review" and {"rent_agreement.landlord", "rent_agreement.tenant"} <= failed(r)


def test_landlord_esign_must_be_the_person_on_the_bill(k02r):
    spec, docs = k02r
    docs = {**docs, "rent_agreement": None}
    ok = evaluate(Declared(spec["gstin"], spec["udyam_number"], spec["business_name"], landlord="Sunita Banerjee"), docs)
    assert ok.outcome == "verified"
    bad = evaluate(Declared(spec["gstin"], spec["udyam_number"], spec["business_name"], landlord="Ramesh Gupta"), docs)
    assert bad.outcome == "review" and "address_proof.name" in failed(bad)


def test_a_bill_in_the_proprietors_own_name_is_the_business(k02r):
    spec, docs = k02r
    bill = docs["address_proof"]
    own = type(bill)(bill.doc_type_detected, bill.quality, {**bill.fields, "billed_to": "Joseph Shah"})
    r = evaluate(Declared(spec["gstin"], spec["udyam_number"], spec["business_name"]), {**docs, "address_proof": own, "rent_agreement": None})
    assert r.outcome == "verified", failed(r)


def test_landlord_link_verifies_kyc_without_a_review():
    with TestClient(app) as c:
        _, oid, key = order(c, {"P01": 1}, "9812345690")
        k = kyc_ok(c, oid, key, "K02R")
        assert k["result"]["outcome"] == "fix_needed"
        fix = next(ch for ch in k["result"]["checks"] if ch["id"] == "address_proof.name")
        assert "Sunita Banerjee" in fix["args"]["local_fix"]
        # the landlord confirms from their own phone
        assert c.post(f"/api/orders/{oid}/landlord?key={key}", json={"phone": "9812345690"}).status_code == 422
        a = c.post(f"/api/orders/{oid}/landlord?key={key}", json={"phone": "9812345691"}).json()
        token = a["link"].split("/approve/")[1].split("?")[0]
        page = c.get(f"/api/approvals/{token}").json()
        assert page["kind"] == "landlord" and page["name_on_bill"] == "Sunita Banerjee" and "Station Road" in page["premises"]
        wrong = c.post(f"/api/approvals/{token}", json={"decision": "approve", "name": "Ramesh Gupta", "otp": "123456", "consent": True})
        assert wrong.status_code == 422
        yes = c.post(f"/api/approvals/{token}", json={"decision": "approve", "name": "Sunita Banerjee", "otp": "123456", "consent": True}).json()
        assert yes["status"] == "approved" and yes["kyc"] == "verified"
        v = c.get(f"/api/orders/{oid}?key={key}").json()
        assert v["status"] == "kyc_verified" and any(e["kind"] == "landlord_confirmed" for e in v["events"])


def test_uploading_the_rent_agreement_verifies_kyc():
    with TestClient(app) as c:
        _, oid, key = order(c, {"P01": 1}, "9812345692")
        assert kyc_ok(c, oid, key, "K02R")["result"]["outcome"] == "fix_needed"
        r = c.post(f"/api/orders/{oid}/kyc/specimen?key={key}", json={"specimen": "K02R", "docs": ["rent_agreement"]}).json()
        assert r["result"]["outcome"] == "verified", r["result"]


# ---- staff prepare, the owner approves -----------------------------------------------------------

def test_staff_order_cannot_be_charged_until_the_owner_approves():
    with TestClient(app) as c:
        assert c.post("/api/orders", json={"profile": {"city": "Jaipur"}, "items": {"P01": 1}, "phone": "9812345693",
                                           "placed_by": "staff"}).status_code == 422  # no owner number
        r = c.post("/api/orders", json={"profile": {"city": "Jaipur"}, "items": {"P01": 1}, "phone": "9812345694",
                                        "placed_by": "staff", "owner_phone": "9812345694"})
        assert r.status_code == 422  # the owner can't be the person placing it
        o, oid, key = order(c, {"P01": 1}, "9812345694", placed_by="staff", owner_phone="9812345695")
        appr = o["approvals"][0]
        assert appr["kind"] == "owner" and appr["status"] == "pending"
        assert any(m["kind"] == "owner_approved" and m["status"] == "pending" for m in o["milestones"])
        assert kyc_ok(c, oid, key)["result"]["outcome"] == "verified"
        pay = {"method": "upi_autopay", "upi_id": "staff@upi"}
        assert c.post(f"/api/orders/{oid}/pay?key={key}", json=pay).status_code == 409
        token = appr["link"].split("/approve/")[1].split("?")[0]
        page = c.get(f"/api/approvals/{token}").json()
        assert page["kind"] == "owner" and page["monthly_paise"] > 0 and page["lines"] and page["prepared_by"].startswith("98")
        assert c.post(f"/api/approvals/{token}", json={"decision": "approve", "name": "Anita Rao", "otp": "12", "consent": True}).status_code == 422
        assert c.post(f"/api/approvals/{token}", json={"decision": "approve", "name": "Anita Rao", "otp": "123456"}).status_code == 403
        yes = c.post(f"/api/approvals/{token}", json={"decision": "approve", "name": "Anita Rao", "otp": "123456", "consent": True}).json()
        assert yes["access_key"] == key  # the owner's phone holds the order too
        assert c.post(f"/api/approvals/{token}", json={"decision": "approve", "name": "x", "otp": "123456", "consent": True}).status_code == 409
        assert c.post(f"/api/orders/{oid}/pay?key={key}", json=pay).status_code == 200
        v = c.get(f"/api/orders/{oid}?key={key}").json()
        assert any(m["kind"] == "owner_approved" and m["status"] == "done" for m in v["milestones"])


def test_owner_can_say_no():
    with TestClient(app) as c:
        o, oid, key = order(c, {"P01": 1}, "9812345696", placed_by="staff", owner_phone="9812345697")
        token = o["approvals"][0]["link"].split("/approve/")[1].split("?")[0]
        c.post(f"/api/approvals/{token}", json={"decision": "decline", "reason": "Too costly"})
        kyc_ok(c, oid, key)
        r = c.post(f"/api/orders/{oid}/pay?key={key}", json={"method": "upi_autopay", "upi_id": "x@upi"})
        assert r.status_code == 409 and "declined" in r.json()["detail"]
        v = c.get(f"/api/orders/{oid}?key={key}").json()
        assert any(m["kind"] == "owner_approved" and m["status"] == "attention" for m in v["milestones"])


# ---- existing Dukaan Connect customers --------------------------------------------------------------------

def test_existing_customer_is_recognised_and_their_numbers_become_business_sims():
    with TestClient(app) as c:
        o, oid, key = order(c, {"P01": 1, "P07": 2}, "9876500001")
        assert o["customer"]["since"] == 2019 and len(o["customer"]["lines"]) == 3
        assert "9876500011" not in str(o["customer"])  # masked
        assert any(e["kind"] == "number_verified" and e["detail"]["method"] == "network" for e in o["events"])
        assert kyc_ok(c, oid, key)["result"]["outcome"] == "verified"
        c.post(f"/api/orders/{oid}/pay?key={key}", json={"method": "upi_autopay", "upi_id": "a@upi"})
        v = book(c, oid, key)
        assert any(e["kind"] == "activation_hold" and e["product_id"] == "P07" for e in v["events"])
        sims = c.get(f"/api/orders/{oid}/sim-users?key={key}").json()
        need = sims["needed"]
        assert need >= 1 and len(sims["existing"]) == 3
        assert c.post(f"/api/orders/{oid}/sim-users/existing?key={key}", json={"line_ids": ["L9"]}).status_code == 422
        r = c.post(f"/api/orders/{oid}/sim-users/existing?key={key}", json={"line_ids": ["L2", "L3", "L1"][:need]}).json()
        assert r["verified"] == need and all(u["on_file"] for u in r["users"]) and r["existing"] == []
        v = c.get(f"/api/orders/{oid}?key={key}").json()
        assert any(e["kind"] == "product_active" and e["product_id"] == "P07" for e in v["events"])


def test_a_new_number_is_not_treated_as_a_customer():
    with TestClient(app) as c:
        o, oid, key = order(c, {"P01": 1}, "9812345698")
        assert o["customer"] is None
        kyc_ok(c, oid, key)
        assert c.post(f"/api/orders/{oid}/sim-users/existing?key={key}", json={"line_ids": ["L1"]}).status_code == 404


# ---- trust: the call code, checking a caller, who opened my documents -----------------------------

def test_call_back_has_a_code_and_callers_can_be_checked():
    with TestClient(app) as c:
        h = c.post("/api/help", json={"phone": "9812345699", "window": "asap"}).json()
        assert len(h["call_code"]) == 4 and h["call_code"].isdigit()
        q = c.get("/api/backoffice/help", headers=staff_headers(c, "ops-1", "ops-demo")).json()
        assert any(r["summary"].get("call_code") == h["call_code"] for r in q)
        assert c.get("/api/verify-caller?q=partner-001").json() == {"genuine": True, "kind": "partner", "name": "Sharma Telecom, Jaipur"}
        assert c.get("/api/verify-caller?q=+91 99999 99999").json() == {"genuine": False}


def test_access_log_shows_who_read_the_documents():
    with TestClient(app) as c:
        _, oid, key = order(c, {"P01": 1}, "9812345700")
        kyc_ok(c, oid, key)
        log = c.get(f"/api/orders/{oid}/access-log?key={key}").json()
        whats = {(e["who"], e["action"], e["what"]) for e in log["entries"]}
        assert ("You", "uploaded", "address proof") in whats
        assert any(w == "Automatic KYC check" and a == "read" for w, a, _ in whats)


# ---- after go-live: set up, not just installed -----------------------------------------------------

def test_setup_is_tracked_after_go_live():
    with TestClient(app) as c:
        _, oid, key = order(c, {"P01": 1, "P16": 3}, "9812345701")
        kyc_ok(c, oid, key)
        c.post(f"/api/orders/{oid}/pay?key={key}", json={"method": "upi_autopay", "upi_id": "a@upi"})
        assert c.post(f"/api/orders/{oid}/setup/P16?key={key}").status_code == 409  # not live yet
        book(c, oid, key)
        a = c.get(f"/api/orders/{oid}/account?key={key}").json()
        t = next(t for t in a["setup_tasks"] if t["product_id"] == "P16")
        assert t["live"] and not t["done"] and t["next_nudge"] == {"day": 3, "how": "whatsapp"}
        ops = staff_headers(c, "ops-1", "ops-demo")
        assert any(r["order_id"] == oid for r in c.get("/api/backoffice/setup-pending", headers=ops).json())
        done = c.post(f"/api/orders/{oid}/setup/P16?key={key}").json()
        assert next(t for t in done["setup_tasks"] if t["product_id"] == "P16")["done"]
        assert not any(r["order_id"] == oid for r in c.get("/api/backoffice/setup-pending", headers=ops).json())
