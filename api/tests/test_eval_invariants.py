"""The advisor eval, as invariants: whatever the owner says, the bundle never breaks a catalogue rule.

600 random profiles through the engine, and a generated set of owner sentences in
several languages through the rules-only advisor (the mode the AI-off demo runs).
Every bundle is checked against the catalogue rules directly, not against an expected
answer: city tier, staff and site minimums, GSTIN, dependencies, per-site caps, quantities.
"""
import itertools
import random

import pytest

from app.advisor.agent import Advisor
from app.data_store import store
from app.engine import graph
from app.engine.profile import Profile
from app.engine.recommend import PER_SITE_ADDONS, price_custom, recommend


def rule_breaks(bundle_lines, prof: Profile) -> list[str]:
    ds = store()
    ids = {ln.product_id if hasattr(ln, "product_id") else ln["product_id"] for ln in bundle_lines}
    out = []
    connected = 0
    for ln in bundle_lines:
        pid = ln.product_id if hasattr(ln, "product_id") else ln["product_id"]
        qty = ln.qty if hasattr(ln, "qty") else ln["qty"]
        p = ds.products[pid]
        if prof.city_tier is not None and prof.city_tier not in p.tiers:
            out.append(f"{pid} sold in tier {prof.city_tier}")
        if p.min_employees > 1 and prof.n_employees < p.min_employees:
            out.append(f"{pid} needs {p.min_employees} staff")
        if p.min_sites > 1 and prof.n_sites < p.min_sites:
            out.append(f"{pid} needs {p.min_sites} sites")
        if p.requires_gstin and not prof.gstin_ok:
            out.append(f"{pid} needs GSTIN")
        if p.requires_one_of and not (set(p.requires_one_of) & ids):
            out.append(f"{pid} missing dependency")
        if not 1 <= qty <= 500:
            out.append(f"{pid} qty {qty}")
        if pid in graph.CONNECTIVITY:
            connected += qty
    for ln in bundle_lines:
        pid = ln.product_id if hasattr(ln, "product_id") else ln["product_id"]
        qty = ln.qty if hasattr(ln, "qty") else ln["qty"]
        if pid in PER_SITE_ADDONS and connected and qty > connected:
            out.append(f"{pid} x{qty} on {connected} connections")
    return out


def random_profiles(n: int, seed: int = 11):
    rng = random.Random(seed)
    needs = sorted(graph.NEED_CHAIN)
    for _ in range(n):
        gst = rng.random() < 0.6
        yield Profile.from_dict({
            "segment": rng.choice(["micro", "prof", "multi", "mfg", None]), "employees": rng.choice([1, 2, 4, 6, 9, 12, 26, 60]),
            "sites": rng.choice([1, 1, 2, 3, 5]), "city_tier": rng.choice([1, 2, 3]), "has_gstin": gst,
            "gstin_status": rng.choice(["Active", "Declared", "Cancelled"]) if gst else None,
            "needs": rng.sample(needs, rng.randint(0, 4)), "only": rng.random() < 0.2, "budget": rng.choice([None, 900, 1500, 5000]),
            "term_months": rng.choice([12, 24]), "fibre_feasible": rng.choice([None, True, False]),
            "qty": {k: rng.randint(1, 12) for k in rng.sample(["users", "devices", "lines", "cameras"], rng.randint(0, 2))},
        })


def test_600_random_profiles_never_break_a_rule():
    broken = [(p.to_dict(), b) for p in random_profiles(600) if (b := rule_breaks(recommend(p).lines, p))]
    assert not broken, broken[:3]


def test_600_random_custom_carts_never_break_a_rule():
    rng = random.Random(5)
    pids = sorted(store().products)
    broken = []
    for p in random_profiles(600, seed=3):
        cart = {pid: rng.randint(-2, 9) for pid in rng.sample(pids, rng.randint(1, 7))}
        b = rule_breaks(price_custom(p, cart).lines, p)
        if b:
            broken.append((cart, b))
    assert not broken, broken[:3]


BUSINESSES = [("kirana shop", "किराना दुकान"), ("dental clinic", "डेंटल क्लिनिक"), ("CA firm", "सीए फर्म"), ("restaurant chain", "रेस्टोरेंट"),
              ("textile factory", "कपड़ा फैक्ट्री"), ("salon", "सैलून")]
CITIES = ["Jaipur", "Pune", "Kochi", "Delhi", "Mumbai", "Vadodara"]
ASKS = ["fast internet", "1 Gbps internet", "a leased line", "WhatsApp Business", "toll-free number", "SD-WAN for all branches",
        "CCTV", "email for everyone", "a firewall", "machine monitoring", "only internet", "backup internet"]


def sentences():
    for (en, hi), city, ask, staff, gst, sites in itertools.islice(
            itertools.product(BUSINESSES, CITIES, ASKS, (2, 12, 30), ("GST registered", "no GST"), (1, 3)), 0, None, 7):
        site_txt = f", {sites} branches" if sites > 1 else ""
        yield f"We are a {en} in {city}, {staff} staff{site_txt}, {gst}. We need {ask}."


@pytest.mark.parametrize("text", list(sentences()))
def test_owner_sentences_never_produce_a_rule_break(text):
    turn, state = Advisor(use_llm=False).respond({}, text)
    if turn.bundle:
        prof = Profile.from_dict(state["profile"])
        if prof.city_tier is None:
            prof.city_tier = 2
        if prof.has_gstin is None and prof.gstin_status is None:
            prof.has_gstin = False
        assert not rule_breaks(turn.bundle["lines"], prof), (text, rule_breaks(turn.bundle["lines"], prof))
