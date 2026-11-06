from fastapi.testclient import TestClient

from app.main import app

PK = {"X-Partner-Key": "accel-demo"}  # demo partner passcode: partner role only


def staff_headers(c, user, secret):
    return {"Authorization": "Bearer " + c.post("/api/staff/login", json={"user": user, "secret": secret}).json()["token"]}


def test_full_journey_k09():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"] == "ok"
        s = c.post("/api/advisor/sessions", json={"language": "en"}).json()
        sid = s["session_id"]
        r = c.post(f"/api/advisor/sessions/{sid}/messages", json={"text": "Insurance agency in Visakhapatnam, 25 staff, GST registered. We need fast internet and email."}).json()
        assert r["turn"]["stage"] == "recommended", r["turn"]["text"]
        items = {ln["product_id"]: ln["qty"] for ln in r["bundle"]["lines"]}
        q = c.post("/api/quote", json={"session_id": sid, "items": items, "term_months": 24}).json()
        assert q["monthly"] > 0 and q["term_months"] == 24
        o = c.post("/api/orders", json={"session_id": sid, "items": items, "term_months": 24, "phone": "98765 43210"}).json()
        oid, key = o["order_id"], o["access_key"]
        assert o["phone_masked"].startswith("98") and "43210" not in o["phone_masked"]
        # KYC before consent is refused
        assert c.post(f"/api/orders/{oid}/kyc/specimen?key={key}", json={"specimen": "K09"}).status_code == 403
        cons = c.post(f"/api/orders/{oid}/consent?key={key}", json={"choices": {"kyc_verification": True, "service_delivery": True, "order_updates": True}}).json()
        assert cons["kyc_verification"]["granted"] and not cons["marketing"]["granted"]
        k = c.post(f"/api/orders/{oid}/kyc/specimen?key={key}", json={"specimen": "K09"}).json()
        assert k["result"]["outcome"] == "verified", k["result"]
        assert c.post(f"/api/orders/{oid}/pay?key={key}", json={"method": "upi_autopay", "upi_id": "anita@upi"}).json()["autopay_mandate"]
        day = c.get(f"/api/orders/{oid}/slots?key={key}").json()["days"][0]
        v = c.post(f"/api/orders/{oid}/schedule?key={key}", json={"slot": f"{day['date']} {day['slots'][0]}"}).json()
        # business SIMs wait for each user's own KYC (DoT): no line goes live before that
        assert any(e["kind"] == "activation_hold" for e in v["events"])
        sims = [ln for ln in v["bundle"]["lines"] if ln["product_id"] in ("P07", "P08")]
        need = sum(ln["qty"] for ln in sims)
        users = [{"name": f"Staff {i}", "phone": f"98000000{i:02d}"} for i in range(need)]
        su = c.post(f"/api/orders/{oid}/sim-users?key={key}", json={"users": users}).json()
        for u in su["users"]:
            assert c.post(f"/api/sim/{u['id']}/verify", json={"method": "digilocker", "consent": True}).json()["status"] == "verified"
        # the last user's verification switches the held SIMs on, with no ops step
        live = {e["product_id"] for e in c.get(f"/api/orders/{oid}?key={key}").json()["events"] if e["kind"] == "product_active"}
        assert {ln["product_id"] for ln in sims} <= live
        for _ in range(10):
            v = c.post(f"/api/orders/{oid}/advance?key={key}").json()
            if v["status"] == "active":
                break
        assert v["status"] == "active"
        assert all(m["status"] == "done" for m in v["milestones"])
        mine = c.get(f"/api/orders/{oid}/my-data?key={key}").json()
        assert mine["identifiers"]["phone"] == "9876543210"
        w = c.post(f"/api/orders/{oid}/consent/order_updates/withdraw?key={key}").json()
        assert not w["order_updates"]["granted"]
        assert c.get(f"/api/orders/{oid}?key=wrong").status_code == 404


def test_tampered_specimen_goes_to_review_and_backoffice_approves():
    with TestClient(app) as c:
        o = c.post("/api/orders", json={"profile": {"segment": "micro", "business_type": "Salon", "employees": 2, "city": "Jaipur", "city_tier": 2},
                                        "items": {"P01": 1, "P07": 1}, "phone": "9811111111", "specimen": "K06"}).json()
        oid, key = o["order_id"], o["access_key"]
        c.post(f"/api/orders/{oid}/consent?key={key}", json={"choices": {"kyc_verification": True, "service_delivery": True}})
        k = c.post(f"/api/orders/{oid}/kyc/specimen?key={key}", json={"specimen": "K06"}).json()
        assert k["result"]["outcome"] == "review"
        assert c.get("/api/backoffice/reviews").status_code == 401
        assert c.get("/api/backoffice/reviews", headers=PK).status_code == 403  # partners can't review KYC
        r1, r2 = staff_headers(c, "reviewer-1", "review-demo"), staff_headers(c, "reviewer-2", "review-demo")
        revs = c.get("/api/backoffice/reviews", headers=r1).json()
        mine = next(r for r in revs if r["id"] == oid)
        assert mine["needs_two_reviewers"]  # a GSTIN mismatch can't be waved through by one person
        first = c.post(f"/api/backoffice/orders/{oid}/review", headers=r1, json={"decision": "approve", "note": "checked original"}).json()
        assert first["status"] == "kyc_review" and first["pending_approval"] == "reviewer-1"
        assert c.post(f"/api/backoffice/orders/{oid}/review", headers=r1, json={"decision": "approve"}).status_code == 409
        assert c.post(f"/api/backoffice/orders/{oid}/review", headers=r2, json={"decision": "approve"}).json()["status"] == "kyc_verified"


def test_missing_udyam_fixed_via_digilocker():
    with TestClient(app) as c:
        o = c.post("/api/orders", json={"profile": {"segment": "prof", "business_type": "Real estate agency", "employees": 23, "city": "Kochi", "city_tier": 2, "has_gstin": True},
                                        "items": {"P02": 1, "P16": 5}, "phone": "9822222222", "specimen": "K05"}).json()
        oid, key = o["order_id"], o["access_key"]
        c.post(f"/api/orders/{oid}/consent?key={key}", json={"choices": {"kyc_verification": True, "service_delivery": True}})
        k = c.post(f"/api/orders/{oid}/kyc/specimen?key={key}", json={"specimen": "K05"}).json()
        assert k["result"]["outcome"] == "fix_needed"
        d = c.post(f"/api/orders/{oid}/kyc/digilocker?key={key}", json={}).json()
        assert d["source"] == "digilocker"
        again = c.post(f"/api/orders/{oid}/kyc/evaluate?key={key}").json()
        assert again["result"]["outcome"] == "verified", [x for x in again["result"]["checks"] if x["status"] == "fail"]


def test_backoffice_and_judge_and_whatsapp():
    with TestClient(app) as c:
        leads = c.get("/api/backoffice/leads?limit=5", headers=PK).json()
        assert len(leads["leads"]) == 5 and leads["model"]["auc"] > 0.65
        call = c.post(f"/api/backoffice/leads/{leads['leads'][0]['lead_id']}/call", headers=PK, json={}).json()
        assert call["virtual_number"].startswith("+91 80")
        m = c.get("/api/backoffice/metrics", headers=PK).json()
        assert m["baseline"]["conversion"] == 0.0736 and m["baseline"]["days_to_activate"] == 17.6
        sc = c.get("/api/judge/scenarios").json()
        assert sc["passed"] == sc["total"]
        wa = c.post("/api/whatsapp/simulate", json={"from_number": "9800000009", "text": "Bakery in Vadodara, 3 staff, no GST"}).json()
        assert "Dukaan Starter" in wa["reply"]
        assert c.get("/api/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "accel-verify", "hub.challenge": "42"}).text == "42"


def test_erase_shreds_documents_and_identifiers():
    from app.db import SessionLocal, Document, Order, VaultEntry
    from app.privacy import crypto
    with TestClient(app) as c:
        o = c.post("/api/orders", json={"profile": {"segment": "prof", "business_type": "Insurance agency", "employees": 25, "city": "Visakhapatnam", "city_tier": 2, "has_gstin": True},
                                        "items": {"P02": 1, "P16": 5}, "phone": "9833333333", "specimen": "K09"}).json()
        oid, key = o["order_id"], o["access_key"]
        c.post(f"/api/orders/{oid}/consent?key={key}", json={"choices": {"kyc_verification": True, "service_delivery": True}})
        assert c.post(f"/api/orders/{oid}/kyc/specimen?key={key}", json={"specimen": "K09"}).json()["result"]["outcome"] == "verified"
        assert c.post(f"/api/orders/{oid}/erase?key={key}").json()["erased"]
    db = SessionLocal()
    try:
        order = db.get(Order, oid)
        docs = db.query(Document).filter(Document.order_id == oid).all()
        assert docs and all(d.deleted_at is not None for d in docs)
        for tok in (order.gstin_token, order.phone_token):
            e = db.get(VaultEntry, tok)
            try:
                crypto.open_(e.wrapped_dek, e.nonce, e.ciphertext, tok.encode())
                raise AssertionError("identifier still decryptable after erasure")
            except PermissionError:
                pass
    finally:
        db.close()


def test_gstin_as_a_follow_up_message_in_telugu():
    """Regression: a GSTIN typed after the first message crashed (saved state held tokens=None)."""
    with TestClient(app) as c:
        sid = c.post("/api/advisor/sessions", json={"language": "te"}).json()["session_id"]
        r = c.post(f"/api/advisor/sessions/{sid}/messages", json={"text": "విశాఖపట్నంలో మా ఇన్సూరెన్స్ ఏజెన్సీ ఉంది, 25 మంది ఉద్యోగులు.", "language": "te"}).json()
        assert r["turn"]["asked"] == "gstin"
        r = c.post(f"/api/advisor/sessions/{sid}/messages", json={"text": "37LDYXK0296F1ZB", "language": "te"})
        assert r.status_code == 200
        body = r.json()
        assert "37LDYXK0296F1ZB" not in str(body["messages"])  # stored masked


def test_no_to_gstin_in_indic_scripts_moves_on():
    """Regression: Python's \\b does not fire after an Indic vowel sign, so 'లేదు' / 'नहीं' were ignored."""
    with TestClient(app) as c:
        for lang, first, no in (("te", "విశాఖపట్నంలో మా ఇన్సూరెన్స్ ఏజెన్సీ ఉంది, 25 మంది ఉద్యోగులు.", "లేదు"),
                                ("hi", "दिल्ली में हमारा डेंटल क्लिनिक है, 6 लोग", "नहीं")):
            sid = c.post("/api/advisor/sessions", json={"language": lang}).json()["session_id"]
            r = c.post(f"/api/advisor/sessions/{sid}/messages", json={"text": first, "language": lang}).json()
            assert r["turn"]["asked"] == "gstin"
            r = c.post(f"/api/advisor/sessions/{sid}/messages", json={"text": no, "language": lang}).json()
            assert r["turn"]["asked"] != "gstin"
