"""Money: every amount shown and charged comes from one payment schedule."""
import random

import pytest
from fastapi.testclient import TestClient

from app.data_store import store
from app.engine import schedule
from app.engine.profile import Profile
from app.engine.recommend import price_custom
from app.main import app


def test_instalments_sum_to_setup():
    for setup in (1, 11, 1000, 2500, 2501, 44000, 99999):
        parts = schedule.instalments(setup)
        assert sum(parts) == setup * 100 and len(parts) == 12
        assert len(set(parts[:-1])) <= 1  # regular instalments, the last absorbs the remainder


def test_rs2500_setup_is_eleven_208s_and_one_212():
    s = schedule.build(1000, 2500, 12, setup_emi=True)
    assert s["instalment"] == 20800 and s["last_instalment"] == 21200
    assert sum(r["setup"] for r in s["rows"]) == 250000


def test_due_today_is_row_zero_and_mandate_covers_every_debit():
    s = schedule.build(4815, 1500, 24, setup_emi=False)
    assert s["due_today"] == s["rows"][0]["total"]
    assert s["due_today"] == 481500 + 86670 + 150000 + 27000  # month 1 + GST, setup + GST, paid upfront
    assert s["mandate_limit"] >= max(r["total"] for r in s["rows"][1:])
    assert s["total_commitment"] == sum(r["total"] for r in s["rows"])


def test_emi_longer_than_term_is_collected_not_dropped():
    s = schedule.build(299, 1200, 6, setup_emi=True)
    assert sum(r["setup"] for r in s["rows"]) == 120000


@pytest.fixture(scope="module")
def products():
    return sorted(store().products)


def test_property_10000_random_carts(products):
    """Quote, charge and mandate all agree with the schedule, for any cart and payment choice."""
    rng = random.Random(7)
    prof = Profile.from_dict({"segment": "multi", "employees": 60, "sites": 5, "city_tier": 1, "has_gstin": True, "gstin_status": "Active"})
    for _ in range(10000):
        items = {p: rng.randint(1, 6) for p in rng.sample(products, rng.randint(1, 6))}
        prof.term_months = rng.choice((12, 24))
        b = price_custom(prof, items).to_dict()
        if not b["lines"]:
            continue
        emi = rng.random() < 0.5
        s = schedule.for_bundle(b, emi)
        rows = s["rows"]
        assert sum(ln["monthly"] for ln in b["lines"]) * 100 == rows[0]["recurring"]
        assert sum(r["setup"] for r in rows) == b["setup"] * 100
        assert all(r["total"] == r["recurring"] + r["setup"] + r["gst"] for r in rows)
        assert s["due_today"] == rows[0]["total"]
        assert s["mandate_limit"] == max(r["total"] for r in rows)
        assert s["total_commitment"] == sum(r["total"] for r in rows)
        assert len(rows) >= b["contract_months"]


def test_api_payment_charges_row_zero_once():
    c = TestClient(app)
    q = c.post("/api/quote", json={"profile": {"segment": "micro", "employees": 2, "city": "Pune", "city_tier": 1, "has_gstin": False},
                                    "items": {"P01": 1, "P19": 1}, "term_months": 12}).json()
    emi = q["schedule_options"]["emi"]
    o = c.post("/api/orders", json={"profile": {"segment": "micro", "employees": 2, "city": "Pune", "city_tier": 1, "has_gstin": False},
                                    "items": {"P01": 1, "P19": 1}, "term_months": 12, "setup_emi": True, "phone": "9876543210"}).json()
    assert o["bundle"]["schedule"]["hash"] == emi["hash"]  # what was quoted is what was ordered
    from app.db import Order, SessionLocal
    db = SessionLocal()
    order = db.get(Order, o["order_id"])
    order.status = "kyc_verified"
    db.commit()
    db.close()
    url = f"/api/orders/{o['order_id']}/pay?key={o['access_key']}"
    p1 = c.post(url, json={"method": "upi_autopay"}).json()
    p2 = c.post(url, json={"method": "upi_autopay"}).json()
    assert p1["amount_paise"] == emi["due_today"] and p1["mandate_limit_paise"] == emi["mandate_limit"]
    assert p1["reference"] == p2["reference"]  # the retry returned the same captured payment
