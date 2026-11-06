"""Advisor fixes from the evaluation: spelling variants, corrections, site counts, budgets, quantities."""
import pytest

from app.advisor.agent import Advisor
from app.advisor.extract import extract
from app.advisor.normalise import loanword_needs
from app.engine.pricing import gst
from app.engine.profile import Profile
from app.engine.recommend import price_custom, recommend


def chat(adv, *msgs, state=None):
    state = state or {}
    turn = None
    for m in msgs:
        turn, state = adv.respond(state, m)
    return turn, state


def ids(turn):
    return {ln["product_id"] for ln in turn.bundle["lines"]}


# ---- spelling variants (rules-only mode is what the AI-off demo runs) ------------

VARIANTS = {
    "whatsapp": ["व्हाट्सऐप", "वाट्सऐप", "व्हाट्सअप", "व्हाट्सएप", "वॉट्सऐप", "வாட்ஸ்அப்", "వాట్సాప్", "ವಾಟ್ಸಾಪ್",
                 "વોટ્સએપ", "হোয়াটসঅ্যাপ", "വാട്ട്സ്ആപ്പ്", "ਵਟਸਐਪ", "whatsap", "watsapp"],
    "cctv": ["सीसीटीवी", "सी सी टी वी", "সিসিটিভি"],
    "website": ["वेबसाइट", "वेबसाईट", "ওয়েবসাইট"],
    "internet": ["इंटरनेट", "ఇంటర్నెట్", "ഇന്റർനെറ്റ്"],
    "backup": ["बैकअप", "ব্যাকআপ"],
    "mobile_lines": ["मोबाइल", "மொபைல்", "মোবাইল"],
}


@pytest.mark.parametrize("need,word", [(n, w) for n, ws in VARIANTS.items() for w in ws])
def test_loanword_variants_are_recognised(need, word):
    assert need in extract(f"{word} चाहिए").needs or need in extract(word).needs


def test_common_words_are_not_loanwords():
    assert loanword_needs("मेरी किराना दुकान है, तीन लोग काम करते हैं, बजट कम है") == set()


def test_hindi_whatsapp_variant_triggers_the_gst_rule():
    adv = Advisor(use_llm=False)
    turn, _ = chat(adv, "पुणे में मेरी किराना दुकान है, 3 लोग, जीएसटी नहीं है, व्हाट्सऐप पर ऑर्डर लेने हैं")
    assert turn.stage == "recommended"
    assert "P15" in {e["product_id"] for e in turn.bundle["exclusions"]}  # named, and refused for GST: not ignored


# ---- corrections stick -------------------------------------------------------------

def test_only_internet_removes_email():
    adv = Advisor(use_llm=False)
    _, s = chat(adv, "CA firm in Pune with 6 staff, GST active. We need email for everyone.")
    turn, s = chat(adv, "I do not need email. Only internet", state=s)
    assert "P16" not in ids(turn)
    assert "email" in s["profile"]["excluded"]


def test_removed_need_never_returns_as_a_default():
    p = Profile.from_dict({"segment": "prof", "employees": 6, "city_tier": 1, "has_gstin": True, "gstin_status": "Active"})
    assert "P16" in {ln.product_id for ln in recommend(p).lines}
    p.apply_needs(set(), {"email"})
    assert "P16" not in {ln.product_id for ln in recommend(p).lines}


def test_hindi_negation_removes_cctv():
    e = extract("कैमरा नहीं चाहिए, सिर्फ इंटरनेट")
    assert "cctv" in e.removed and "internet" in e.needs


def test_no_fibre_still_wants_internet():
    e = extract("no fibre at my pin code, need internet")
    assert "internet" in e.needs and "internet" not in e.removed


# ---- sites add up ------------------------------------------------------------------

@pytest.mark.parametrize("text,sites", [
    ("2 shops in Jaipur and 1 in Ajmer", 3),
    ("3 stores in Pune, 2 in Mumbai", 5),
    ("we have 4 outlets", 4),
])
def test_sites_are_summed(text, sites):
    assert extract(text).sites == sites


# ---- budget is all-in --------------------------------------------------------------

def test_budget_counts_gst():
    p = Profile.from_dict({"segment": "micro", "employees": 2, "city_tier": 2, "has_gstin": False, "budget": 1100,
                           "needs": ["internet"], "only": True})
    b = recommend(p)
    total = b.monthly + gst(b.monthly)
    assert total <= 1100 or any(n["code"] == "over_budget" for n in b.notes)


# ---- quantities --------------------------------------------------------------------

def test_negative_and_huge_quantities_are_clamped():
    p = Profile.from_dict({"segment": "prof", "employees": -5, "sites": -2, "qty": {"users": -4, "lines": 10**9}})
    assert p.employees == 1 and p.sites == 1
    assert "users" not in p.qty and p.qty["lines"] == 500


def test_custom_cart_rejects_negative_quantity():
    p = Profile.from_dict({"segment": "prof", "employees": 6, "city_tier": 1, "has_gstin": True, "gstin_status": "Active"})
    b = price_custom(p, {"P02": 1, "P16": -3})
    assert all(ln.monthly >= 0 for ln in b.lines) and "P16" not in {ln.product_id for ln in b.lines}


def test_sdwan_units_capped_by_connected_sites():
    p = Profile.from_dict({"segment": "multi", "employees": 40, "sites": 4, "city_tier": 1, "has_gstin": True, "gstin_status": "Active"})
    b = price_custom(p, {"P02": 1, "P10": 4})
    sdwan = next(ln for ln in b.lines if ln.product_id == "P10")
    assert sdwan.qty == 1
    assert any(n["code"] == "per_site_cap" for n in b.notes)
