"""Rules the advisor must keep for any wording: named features, leased lines only on request,
the speed asked for, sites counted once, and a person only when the owner asks."""
import pytest

from app.advisor.agent import Advisor
from app.advisor.extract import extract
from app.engine.profile import Profile
from app.engine.recommend import recommend


def ids(bundle) -> set[str]:
    return {ln.product_id for ln in bundle.lines}


def prof(**kw) -> Profile:
    return Profile.from_dict({"city": "Pune", "city_tier": 1, "employees": 4, "has_gstin": False, **kw})


# ---- engine: what the owner insists on ---------------------------------------------

@pytest.mark.parametrize("extra", [{"features": ["roaming"]}, {"features": ["priority_support"]}, {"data_gb": 100}])
def test_a_named_feature_picks_the_plan_that_has_it(extra):
    b = recommend(prof(segment="micro", needs=["mobile_lines"], only=True, **extra))
    assert ids(b) == {"P08"}


def test_without_a_feature_micro_keeps_the_cheaper_line():
    assert ids(recommend(prof(segment="micro", needs=["mobile_lines"], only=True))) == {"P07"}


def test_a_tight_budget_never_trades_away_a_named_feature():
    b = recommend(prof(segment="micro", needs=["mobile_lines"], only=True, features=["roaming"], budget=500))
    assert "P08" in ids(b) and any(n["code"] == "over_budget" for n in b.notes)


def test_a_leased_line_is_never_added_just_to_unlock_an_add_on():
    b = recommend(prof(segment="prof", employees=12, has_gstin=True, gstin_status="Active", fibre_feasible=False, needs=["firewall"]))
    assert not ids(b) & {"P05", "P06"} and "P21" not in ids(b)
    refused = {e.product_id: e for e in b.exclusions}
    assert refused["P21"].rule == "line_on_request" and refused["P21"].alternative_id == "P20" and "P20" in ids(b)


def test_a_dependency_connection_for_a_factory_is_broadband_not_a_leased_line():
    b = recommend(prof(segment="mfg", employees=30, has_gstin=True, gstin_status="Active", needs=["cctv"], only=True))
    assert "P23" in ids(b) and not ids(b) & {"P05", "P06"}


def test_a_cheap_broadband_line_may_still_carry_an_add_on_beside_a_leased_line():
    b = recommend(prof(segment="mfg", employees=20, has_gstin=True, gstin_status="Active", needs=["dedicated_line", "guest_wifi"]))
    assert {"P05", "P22"} <= ids(b) and ids(b) & {"P01", "P02", "P03", "P04"}


def test_once_the_owner_asks_for_the_leased_line_the_add_on_comes_back():
    b = recommend(prof(segment="prof", employees=12, has_gstin=True, gstin_status="Active", fibre_feasible=False,
                       needs=["firewall", "dedicated_line"]))
    assert {"P05", "P21"} <= ids(b) and "P04" not in ids(b)


@pytest.mark.parametrize("want, tier, expect, refused", [(500, 1, "P03", None), (200, 1, "P02", None), (500, 2, "P02", "P03"),
                                                         (100, 1, "P02", None), (2000, 1, "P03", None)])
def test_the_slowest_line_that_meets_the_speed_asked(want, tier, expect, refused):
    b = recommend(prof(segment="prof", employees=6, city_tier=tier, has_gstin=True, gstin_status="Active", speed_mbps=want))
    assert expect in ids(b)
    if refused:
        assert any(e.product_id == refused for e in b.exclusions)


def office(**kw) -> Profile:
    return prof(**{"segment": "prof", "employees": 5, "city": "Delhi", "has_gstin": True, "gstin_status": "Active", "needs": ["internet"],
                   "only": True, **kw})


@pytest.mark.parametrize("speed, budget, kept, option, fits", [(1000, 1500, "P03", "P01", True), (1000, 2500, "P03", "P02", True),
                                                               (300, 1500, "P02", "P01", True), (1000, 900, "P03", "P04", False)])
def test_a_tight_budget_never_trades_away_a_named_speed(speed, budget, kept, option, fits):
    b = recommend(office(speed_mbps=speed, budget=budget))
    note = next(n for n in b.notes if n["code"] == "speed_kept")
    assert ids(b) == {kept} and note["option_id"] == option and note["option_fits"] is fits
    assert any(n["code"] == "over_budget" for n in b.notes)
    assert (note["option_monthly"] <= budget) is fits


def test_where_the_named_speed_is_not_sold_the_fastest_line_here_is_kept():
    from app.advisor.agent import speed_text
    b = recommend(office(city="Jaipur", city_tier=2, speed_mbps=1000, budget=1500))
    note = next(n for n in b.notes if n["code"] == "speed_kept")
    assert ids(b) == {"P02"} and not note["reaches"] and any(e.product_id == "P03" for e in b.exclusions)
    assert "fastest line I can offer here is Biz Fibre 300" in speed_text(b.to_dict()["notes"], "en")


def test_without_a_named_speed_the_budget_still_picks_a_cheaper_line():
    b = recommend(office(budget=1500))
    assert ids(b) == {"P01"} and not any(n["code"] == "speed_kept" for n in b.notes)


def test_a_named_speed_inside_the_budget_needs_no_note():
    b = recommend(office(speed_mbps=1000, budget=6000))
    assert ids(b) == {"P03"} and not b.notes


def test_a_line_changed_twice_names_the_first_one():
    b = recommend(office(budget=500))
    ln = next(ln for ln in b.lines if ln.product_id == "P04")
    assert ln.reason["instead_of"] == "P02"
    assert next(n for n in b.notes if n["code"] == "budget_fit")["changed"] == ["Biz Fibre 300 -> Biz 5G AirFiber 100"]


def test_the_owner_hears_the_speed_against_the_budget():
    turn, _ = Advisor(use_llm=False).respond({}, "Clinic in Delhi, 5 staff, GST active. I need 1 Gbps internet only, budget ₹1,500 a month.")
    assert {ln["product_id"] for ln in turn.bundle["lines"]} == {"P03"}
    assert "You asked for 1 Gbps" in turn.text and "Biz Fibre 100 (100 Mbps)" in turn.text and "within your budget" in turn.text
    assert "The closest I can get" not in turn.text  # one sentence about the budget, not two


@pytest.mark.parametrize("follow, line", [("ok, 100 Mbps is fine", "P02"), ("fine, stay within budget", "P02"),
                                          ("the cheaper one please", "P02"), ("ठीक है, बजट में ही रखो", "P02"), ("no, keep 1 Gbps", "P03")])
def test_the_owner_settles_speed_against_budget(follow, line):
    adv = Advisor(use_llm=False)
    _, st = adv.respond({}, "Clinic in Delhi, 5 staff, GST active. I need 1 Gbps internet only, budget 2500 a month.")
    turn, _ = adv.respond(st, follow)
    assert {ln["product_id"] for ln in turn.bundle["lines"]} == {line}


# ---- understanding: wording that must and must not count ------------------------------

@pytest.mark.parametrize("text", ["GST yes", "gst: yes", "GSTIN - available", "yes we have GST", "haan, gst hai", "registered under GST"])
def test_gst_said_yes_many_ways(text):
    assert extract(text).has_gstin is True


@pytest.mark.parametrize("text, budget", [("I can only spend 700 a month", 700), ("we can afford 1,000", 1000), ("budget 2,000 including GST", 2000),
                                          ("1500 tak ka plan", 1500), ("can't go above 1200 a month", 1200), ("not more than 900", 900)])
def test_what_the_owner_can_pay_is_a_budget(text, budget):
    e = extract(text)
    assert e.budget == budget and e.current_spend is None


@pytest.mark.parametrize("text", ["we pay 900 now for a hotspot", "currently spending Rs 1,200 a month"])
def test_what_they_pay_today_is_not_a_budget(text):
    e = extract(text)
    assert e.current_spend and e.budget is None


@pytest.mark.parametrize("text", ["under 300 mbps is fine", "less than 100 mbps", "below 500 GB"])
def test_speeds_and_sizes_are_not_budgets(text):
    assert extract(text).budget is None


@pytest.mark.parametrize("text", ["we cannot get fibre, the building does not allow it", "fibre doesn't reach our lane",
                                  "no wired internet reaches here", "फाइबर नहीं है हमारे यहाँ", "fibre is unavailable on our street"])
def test_fibre_unavailable_many_ways(text):
    e = extract(text)
    assert e.fibre_feasible is False and "internet" not in e.removed


@pytest.mark.parametrize("text", ["we want fibre and have no GST", "fibre with no lock-in please", "I don't want fibre, just SIMs",
                                  "need fibre, not GST registered", "our airfiber is not fast enough"])
def test_fibre_not_mistaken_for_unavailable(text):
    assert extract(text).fibre_feasible is None


@pytest.mark.parametrize("text, sites", [("2 shops in Jaipur and 1 in Ajmer", 3), ("2 clinics, one in Pune and one in Nashik", 2),
                                         ("3 tea stalls in Jaipur", 3), ("we run 3 pharmacies", 3), ("আমাদের ৩টি দোকান", 3)])
def test_sites_counted_once(text, sites):
    assert extract(text).sites == sites


@pytest.mark.parametrize("text, staff", [("4 teachers", 4), ("2 doctors and 3 nurses", 5), ("3 doctors, 8 staff in all", 8),
                                         ("4 doctors and 2 receptionists", 6)])
def test_people_counted_by_role_when_no_total(text, staff):
    assert extract(text).employees == staff


@pytest.mark.parametrize("text, city", [("கோயம்புத்தூரில் என் உணவகம்", "Coimbatore"), ("ಬೆಂಗಳೂರಿನಲ್ಲಿ ಸಲೂನ್", "Bengaluru"),
                                        ("കൊച്ചിയിൽ എന്റെ ക്ലിനിക്", "Kochi")])
def test_city_with_a_case_ending(text, city):
    assert extract(text).city == city


def test_roaming_asks_for_mobile_lines():
    e = extract("4 SIM cards with roaming for my sales team")
    assert "roaming" in e.features and "mobile_lines" in e.needs and e.qty.get("lines") == 4


# ---- the agent: a person only when the owner asks ---------------------------------------

class HandsOff:
    provider, model = "fake", "fake-1"

    def __init__(self, reason):
        self.reason = reason

    def run(self, system, history, tools, execute, max_steps=5, context=None):
        execute("update_profile", {"business_type": "Travel agency", "segment": "prof", "employees": 5, "city": "Jaipur",
                                   "has_gstin": True, "gstin_status": "Cancelled", "needs": ["toll_free"]})
        execute("request_human", {"reason": self.reason})
        return "I've opened a call-back form for you.", []


def test_a_blocked_rule_gets_a_recommendation_not_a_handoff():
    turn, _ = Advisor(llm=HandsOff("other")).respond({}, "Travel agency in Jaipur, 5 staff, GST cancelled, want toll-free")
    assert turn.stage == "recommended" and turn.bundle and "call-back" not in turn.text
    assert any(e["product_id"] == "P13" and e["rule"] == "gstin_inactive" for e in turn.bundle["exclusions"])


@pytest.mark.parametrize("reply", ["Business type is missing. Profile already has the rest. Ask one question.",
                                   "The owner wants email only, so I will call the recommend tool."])
def test_notes_to_itself_never_reach_the_owner(reply):
    class Narrator(HandsOff):
        def run(self, system, history, tools, execute, max_steps=5, context=None):
            execute("update_profile", {"employees": 10, "city": "Chennai", "has_gstin": True, "needs": ["email"], "only_these_needs": True})
            return reply, []
    turn, _ = Advisor(llm=Narrator(None)).respond({}, "Only need business email for our 10 employees, Chennai, GST yes")
    assert reply not in turn.text and not turn.guard["passed"]


def test_the_model_is_told_what_is_still_needed():
    from app.advisor.agent import context_for
    named = Profile.from_dict({"employees": 10, "city": "Chennai", "city_tier": 1, "has_gstin": True, "needs": ["email"], "only": True})
    assert "nothing, call recommend" in context_for(named, "en")
    assert "employees" in context_for(Profile.from_dict({"business_type": "Salon", "segment": "micro"}), "en")


def test_asking_for_a_person_still_hands_off():
    turn, _ = Advisor(llm=HandsOff("other")).respond({}, "please talk to a person, call me")
    assert turn.stage == "handoff"


def test_with_the_model_the_server_states_the_speed_against_the_budget():
    seen = {}

    class Gigabit(HandsOff):
        def run(self, system, history, tools, execute, max_steps=5, context=None):
            execute("update_profile", {"business_type": "Clinic", "segment": "prof", "employees": 5, "city": "Delhi", "has_gstin": True,
                                       "needs": ["high_speed"], "only_these_needs": True, "speed_mbps": 1000, "budget": 1500})
            seen.update(execute("recommend", {}))
            return "Here is the line for your clinic: {{product:P03}}, {{monthly_all_in}} a month with GST.", []
    turn, _ = Advisor(llm=Gigabit(None)).respond({}, "Clinic in Delhi, 5 staff, GST active, 1 Gbps, budget 1500")
    assert turn.guard["passed"] and "speed_mbps 100 " in seen["speed_vs_budget"]
    assert turn.text.count("You asked for 1 Gbps") == 1 and "Biz Fibre 100 (100 Mbps)" in turn.text
