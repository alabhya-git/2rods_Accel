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
from app.engine.recommend import PER_SITE_ADDONS, price_custom, recommend, violations


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
            "features": rng.sample(sorted(graph.FEATURES), rng.randint(0, 1)), "data_gb": rng.choice([None, None, 30, 100, 500]),
            "speed_mbps": rng.choice([None, None, 100, 300, 500, 1000]), "uptime_pct": rng.choice([None, None, 99.5, 99.9]),
            "qty": {k: rng.randint(1, 12) for k in rng.sample(["users", "devices", "lines", "cameras"], rng.randint(0, 2))},
        })


def test_600_random_profiles_never_break_a_rule():
    broken = [(p.to_dict(), b) for p in random_profiles(600) if (b := rule_breaks(recommend(p).lines, p))]
    assert not broken, broken[:3]


def test_600_random_profiles_keep_what_the_owner_asked_for():
    """No leased line the owner did not ask for (or a factory's own default line); named mobile features honoured;
    a named speed met whenever a line that fast is allowed; going over budget is always said."""
    ds = store()
    broken = []
    for p in random_profiles(600, seed=23):
        b = recommend(p)
        got = {ln.product_id for ln in b.lines}
        wants_sla = "dedicated_line" in p.needs or (p.uptime_pct or 0) >= 99.5 or (
            # a factory's own line is the line, not an extra: "only internet" still gets it
            p.segment == "mfg" and p.n_employees >= 10 and not p.needs & {"high_speed", "dedicated_line"} and "internet" not in p.excluded)
        if got & set(graph.LEASED) and not wants_sla:
            broken.append(("leased line not asked for", p.to_dict(), sorted(got)))
        mobile = got & {"P07", "P08"}
        if mobile and (p.features or p.data_gb) and mobile != set(graph.fits(("P07", "P08"), ds.products, p.features, p.data_gb)) & mobile:
            broken.append(("named feature dropped", p.to_dict(), sorted(got)))
        line = got & set(graph.BROADBAND)
        if p.speed_mbps and line and not got & set(graph.LEASED):  # with a budget too: the conflict is said, not settled
            fast_enough = [q for q in graph.BROADBAND if (graph.speed_mbps(ds.products[q].description) or 0) >= p.speed_mbps
                           and not violations(ds.products[q], p)]
            if fast_enough and not any((graph.speed_mbps(ds.products[q].description) or 0) >= p.speed_mbps for q in line):
                broken.append(("slower than asked", p.to_dict(), sorted(got)))
        kept = next((n for n in b.notes if n["code"] == "speed_kept"), None)
        if kept and (b.monthly + b.gst_monthly <= p.budget or kept["product_id"] not in got
                     or kept.get("option_fits") and kept["option_monthly"] > p.budget):
            broken.append(("speed note wrong", p.to_dict(), kept))
        if p.budget and b.monthly + b.gst_monthly > p.budget and not any(n["code"] == "over_budget" for n in b.notes):
            broken.append(("over budget, not said", p.to_dict(), b.monthly))
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
