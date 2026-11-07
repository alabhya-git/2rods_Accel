"""Judge-style advisor scenarios, derived from the catalogue rules.

Each scenario has the owner's words (used by the advisor tests and shown in the judge
console) and the structured profile the advisor should extract from them. The rules
engine is checked against the profile; the advisor is checked end to end separately.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..engine.profile import Profile
from ..engine.recommend import price_custom, recommend
from ..engine.pricing import unit_price
from ..data_store import store


@dataclass
class Scenario:
    id: str
    title: str
    says: str
    profile: dict
    include: list[str] = field(default_factory=list)
    exclude: dict[str, str] = field(default_factory=dict)  # product -> rule that must refuse it
    absent: list[str] = field(default_factory=list)
    qty: dict[str, int] = field(default_factory=dict)
    any_of: list[list[str]] = field(default_factory=list)  # at least one of each group present
    only: list[str] | None = None
    max_monthly: int | None = None
    contract: dict[str, int] = field(default_factory=dict)
    install_days: int | None = None
    setup: int | None = None
    custom: dict[str, int] | None = None  # price an owner-edited cart instead


GST_ACTIVE = {"has_gstin": True, "gstin_status": "Active"}

SCENARIOS: list[Scenario] = [
    Scenario("S01", "1 Gbps asked in a tier-2 city", "We are a dental clinic in Kochi with 8 staff. We need 1 Gbps internet.",
             {"business_type": "Dental clinic", "segment": "prof", "employees": 8, "city": "Kochi", "city_tier": 2, **GST_ACTIVE, "needs": {"high_speed"}},
             include=["P02"], exclude={"P03": "tier"}),
    Scenario("S02", "WhatsApp catalogue without a GSTIN", "Kirana store in Bhopal, 2 people, no GST yet. I want a WhatsApp catalogue for customers.",
             {"business_type": "Kirana store", "segment": "micro", "employees": 2, "city": "Bhopal", "city_tier": 2, "has_gstin": False, "needs": {"whatsapp"}},
             include=["P18"], exclude={"P15": "gstin_missing"}),
    Scenario("S03", "Toll-free with a cancelled GSTIN", "Travel agency in Pune, 6 staff, our GSTIN is cancelled. We want a toll-free number.",
             {"business_type": "Travel agency", "segment": "prof", "employees": 6, "city": "Pune", "city_tier": 1, "has_gstin": True, "gstin_status": "Cancelled", "needs": {"toll_free"}},
             exclude={"P13": "gstin_inactive"}, absent=["P13", "P15", "P14", "P12"]),
    Scenario("S04", "SD-WAN for only 2 outlets", "Restaurant chain with 2 outlets in Indore and 12 staff, GST registered. We want SD-WAN.",
             {"business_type": "Restaurant chain", "segment": "multi", "employees": 12, "sites": 2, "city": "Indore", "city_tier": 2, **GST_ACTIVE, "needs": {"sdwan"}},
             include=["P09"], exclude={"P10": "min_sites"}),
    Scenario("S05", "CCTV only", "I only want CCTV cameras for my boutique in Surat. 3 staff.",
             {"business_type": "Boutique", "segment": "micro", "employees": 3, "city": "Surat", "city_tier": 2, "has_gstin": False, "needs": {"cctv"}, "only": True},
             include=["P23"], any_of=[["P01", "P02", "P03", "P04", "P05", "P06"]]),
    Scenario("S06", "Static IP where only AirFiber works", "My pin code has no fibre. I only need a static IP for CCTV remote view.",
             {"business_type": "Pharmacy", "segment": "micro", "employees": 3, "city": "Nashik", "city_tier": 2, "has_gstin": False, "fibre_feasible": False, "needs": {"static_ip"}, "only": True},
             absent=["P11"], exclude={"P11": "dependency_unmet"}),
    Scenario("S07", "Leased line for a 5-person office", "CA firm in Mumbai, 5 people, GST registered. Give me a leased line.",
             {"business_type": "CA firm", "segment": "prof", "employees": 5, "city": "Mumbai", "city_tier": 1, **GST_ACTIVE, "needs": {"dedicated_line"}},
             include=["P02"], exclude={"P05": "min_employees"}),
    Scenario("S08", "99.9% uptime for a 30-person plant", "Auto-parts unit in Pune, 30 workers, GST active. Internet must never go down, 99.9% uptime.",
             {"business_type": "Auto-parts unit", "segment": "mfg", "employees": 30, "city": "Pune", "city_tier": 1, **GST_ACTIVE, "needs": {"dedicated_line"}, "uptime_pct": 99.9},
             include=["P06"], contract={"P06": 24}, install_days=30),
    Scenario("S09", "Fibre not feasible at the pin code", "Salon in Jaipur, 3 staff, pin code 302001. Fibre is not available on my street.",
             {"business_type": "Salon", "segment": "micro", "employees": 3, "city": "Jaipur", "city_tier": 2, "pincode": "302001", "fibre_feasible": False, "has_gstin": False},
             include=["P04"], exclude={"P01": "not_feasible"}),
    Scenario("S10", "Only a mobile plan", "I only want a mobile plan for my mobile repair shop. 2 people.",
             {"business_type": "Mobile repair shop", "segment": "micro", "employees": 2, "city": "Lucknow", "city_tier": 2, "has_gstin": False, "needs": {"mobile_lines"}, "only": True},
             only=["P07"]),
    Scenario("S11", "Machine IoT for 8 workers", "Textile unit in Surat, 8 workers, GST active. I want machine monitoring.",
             {"business_type": "Textile unit", "segment": "mfg", "employees": 8, "city": "Surat", "city_tier": 2, **GST_ACTIVE, "needs": {"iot"}},
             exclude={"P24": "min_employees"}, absent=["P24"]),
    Scenario("S12", "Cloud telephony for 2 staff", "CA firm with 2 staff in Nagpur, GST registered. We want cloud telephony with IVR.",
             {"business_type": "CA firm", "segment": "prof", "employees": 2, "city": "Nagpur", "city_tier": 2, **GST_ACTIVE, "needs": {"telephony"}},
             include=["P08"], exclude={"P12": "min_employees"}),
    Scenario("S13", "Email for 6 staff", "Architecture studio, 6 staff in Bengaluru. Only business email please.",
             {"business_type": "Architecture studio", "segment": "prof", "employees": 6, "city": "Bengaluru", "city_tier": 1, **GST_ACTIVE, "needs": {"email"}, "only": True},
             only=["P16"], qty={"P16": 6}),
    Scenario("S14", "Four stores, central management", "Electronics retail chain, 4 stores in Chennai, 15 staff, GST active. Manage all stores centrally.",
             {"business_type": "Electronics retail chain", "segment": "multi", "employees": 15, "sites": 4, "city": "Chennai", "city_tier": 1, **GST_ACTIVE, "needs": {"sdwan"}},
             include=["P10", "P09"], qty={"P10": 4, "P09": 4}),
    Scenario("S15", "Budget of Rs 1,500 a month", "Kirana in Patna, 2 people, my budget is Rs 1500 a month.",
             {"business_type": "Kirana store", "segment": "micro", "employees": 2, "city": "Patna", "city_tier": 2, "has_gstin": False, "budget": 1500},
             max_monthly=1500, any_of=[["P01", "P04"]]),
    Scenario("S16", "Logistics firm with 12 trucks", "We run 12 trucks from Ludhiana, 14 staff. Need vehicle tracking.",
             {"business_type": "Logistics firm", "segment": "multi", "employees": 14, "sites": 1, "city": "Ludhiana", "city_tier": 2, **GST_ACTIVE, "needs": {"fleet"}, "qty": {"vehicles": 12}, "only": True},
             only=["P25"], qty={"P25": 12}),
    Scenario("S17", "Fibre contract is 12 months minimum", "Can I get fibre on a one-month contract? Bakery, 3 staff, Vadodara.",
             {"business_type": "Bakery", "segment": "micro", "employees": 3, "city": "Vadodara", "city_tier": 2, "has_gstin": False},
             include=["P01"], contract={"P01": 12, "P07": 1}),
    Scenario("S18", "Leased line in a tier-2 city", "Packaging unit in Coimbatore, 15 workers, GST active, needs a dedicated line.",
             {"business_type": "Packaging unit", "segment": "mfg", "employees": 15, "city": "Coimbatore", "city_tier": 2, **GST_ACTIVE, "needs": {"dedicated_line"}},
             include=["P05"], setup=None),
    Scenario("S19", "1 Gbps for 3 staff in a tier-1 city", "Coaching centre in Delhi, 3 staff, GST active, we want 1 Gbps.",
             {"business_type": "Coaching centre", "segment": "prof", "employees": 3, "city": "Delhi", "city_tier": 1, **GST_ACTIVE, "needs": {"high_speed"}},
             include=["P02"], exclude={"P03": "min_employees"}),
    Scenario("S20", "1 Gbps without a GSTIN", "Diagnostic lab in Hyderabad, 10 staff, no GST registration. 1 Gbps please.",
             {"business_type": "Diagnostic lab", "segment": "prof", "employees": 10, "city": "Hyderabad", "city_tier": 1, "has_gstin": False, "needs": {"high_speed"}},
             include=["P02"], exclude={"P03": "gstin_missing"}),
    Scenario("S21", "Managed firewall for 6 staff", "Law office, 6 staff, Kolkata, GST active. We want a managed firewall.",
             {"business_type": "Law office", "segment": "prof", "employees": 6, "city": "Kolkata", "city_tier": 1, **GST_ACTIVE, "needs": {"firewall"}},
             include=["P20"], exclude={"P21": "min_employees"}),
    Scenario("S22", "Guest Wi-Fi beside a leased line", "Food processing unit, 20 workers in Ahmedabad, GST active, leased line plus guest Wi-Fi for visitors.",
             {"business_type": "Food processing unit", "segment": "mfg", "employees": 20, "city": "Ahmedabad", "city_tier": 1, **GST_ACTIVE, "needs": {"dedicated_line", "guest_wifi"}},
             include=["P05", "P22"], any_of=[["P01", "P02", "P03", "P04"]]),
    Scenario("S23", "WhatsApp with a suspended GSTIN", "Sweet shop in Indore, our GST is suspended. Need WhatsApp business.",
             {"business_type": "Sweet shop", "segment": "micro", "employees": 4, "city": "Indore", "city_tier": 2, "has_gstin": True, "gstin_status": "Suspended", "needs": {"whatsapp"}},
             include=["P18"], exclude={"P15": "gstin_inactive"}),
    Scenario("S24", "Clinic defaults", "Physiotherapy clinic in Delhi, 5 staff, GST active.",
             {"business_type": "Physiotherapy clinic", "segment": "prof", "employees": 5, "city": "Delhi", "city_tier": 1, **GST_ACTIVE},
             include=["P02", "P16", "P20", "P17", "P08"], qty={"P16": 5}),
    Scenario("S25", "SD-WAN with 3 sites but 9 staff", "Gym chain with 3 gyms in Mysuru, 9 staff in total, GST active. SD-WAN please.",
             {"business_type": "Gym chain", "segment": "multi", "employees": 9, "sites": 3, "city": "Mysuru", "city_tier": 2, **GST_ACTIVE, "needs": {"sdwan"}},
             include=["P09"], exclude={"P10": "min_employees"}, qty={"P09": 3}),
    Scenario("S26", "24-month plan is priced at the floor", "Pharmacy in Pune, 3 staff, 24 months.",
             {"business_type": "Pharmacy", "segment": "micro", "employees": 3, "city": "Pune", "city_tier": 1, "has_gstin": False, "term_months": 24},
             include=["P01", "P07", "P19"]),
    Scenario("S27", "Editing the cart cannot buy an ineligible product", "(owner adds Biz Fibre 1G to the cart in Kochi)",
             {"business_type": "Dental clinic", "segment": "prof", "employees": 8, "city": "Kochi", "city_tier": 2, **GST_ACTIVE},
             custom={"P03": 1, "P16": 8}, absent=["P03"], exclude={"P03": "tier"}, include=["P16"]),
    Scenario("S28", "CCTV added to a cart with no connection", "(owner keeps only CCTV in the cart)",
             {"business_type": "Boutique", "segment": "micro", "employees": 2, "city": "Delhi", "city_tier": 1, "has_gstin": False},
             custom={"P23": 2}, include=["P23"], any_of=[["P01", "P02", "P03", "P04", "P05", "P06"]]),
    Scenario("S29", "SIMs with roaming get the plan that has roaming", "Just need 4 business SIM cards with roaming for my sales team in Delhi.",
             {"segment": None, "employees": 6, "city": "Delhi", "city_tier": 1, **GST_ACTIVE, "needs": {"mobile_lines"}, "only": True,
              "features": {"roaming"}, "qty": {"lines": 4}},
             only=["P08"], qty={"P08": 4}),
    Scenario("S30", "Firewall where fibre cannot reach", "Our building does not allow fibre. 12 staff in Pune, GST active. We want a managed firewall.",
             {"business_type": "Office", "segment": "prof", "employees": 12, "city": "Pune", "city_tier": 1, **GST_ACTIVE, "fibre_feasible": False,
              "needs": {"firewall"}},
             include=["P04", "P20"], absent=["P21", "P05", "P06"], exclude={"P21": "line_on_request"}),
    Scenario("S31", "At least 500 Mbps", "Need at least 500 Mbps for my design studio in Pune, 6 staff, GST active.",
             {"business_type": "Architecture studio", "segment": "prof", "employees": 6, "city": "Pune", "city_tier": 1, **GST_ACTIVE, "speed_mbps": 500},
             include=["P03"]),
    Scenario("S32", "99.5% uptime and 1 Gbps, but only 6 staff", "Clinic in Mumbai, 6 staff, GST active: 1 Gbps with 99.5% uptime.",
             {"business_type": "Clinic", "segment": "prof", "employees": 6, "city": "Mumbai", "city_tier": 1, **GST_ACTIVE, "speed_mbps": 1000, "uptime_pct": 99.5},
             include=["P03"], absent=["P05", "P06"], exclude={"P06": "min_employees"}),
]


def _check(s: Scenario) -> tuple[bool, list[str], dict]:
    prof = Profile.from_dict(s.profile)
    bundle = price_custom(prof, s.custom) if s.custom else recommend(prof)
    ids = set(bundle.product_ids)
    problems: list[str] = []
    for pid in s.include:
        if pid not in ids:
            problems.append(f"expected {pid} in bundle")
    for pid in s.absent:
        if pid in ids:
            problems.append(f"{pid} must not be sold")
    for pid, rule in s.exclude.items():
        ex = next((e for e in bundle.exclusions if e.product_id == pid), None)
        if not ex:
            problems.append(f"expected {pid} refused with rule {rule}")
        elif ex.rule != rule:
            problems.append(f"{pid} refused with {ex.rule}, expected {rule}")
    for pid, q in s.qty.items():
        ln = next((ln for ln in bundle.lines if ln.product_id == pid), None)
        if not ln or ln.qty != q:
            problems.append(f"expected {pid} x{q}, got {ln.qty if ln else 0}")
    for group in s.any_of:
        if not ids & set(group):
            problems.append(f"expected one of {group}")
    if s.only is not None and ids != set(s.only):
        problems.append(f"expected only {s.only}, got {sorted(ids)}")
    if s.max_monthly is not None and bundle.monthly > s.max_monthly:
        problems.append(f"monthly {bundle.monthly} over {s.max_monthly}")
    for pid, months in s.contract.items():
        ln = next((ln for ln in bundle.lines if ln.product_id == pid), None)
        if not ln or ln.contract_months != months:
            problems.append(f"expected {pid} contract {months}, got {ln.contract_months if ln else None}")
    if s.install_days is not None and bundle.install_days != s.install_days:
        problems.append(f"install days {bundle.install_days}, expected {s.install_days}")
    if prof.term_months >= 24:
        for ln in bundle.lines:
            if ln.unit_price != store().products[ln.product_id].price_min:
                problems.append(f"{ln.product_id} not at floor on 24 months")
    # universal invariants: every line is eligible and every dependency met
    from ..engine.recommend import violations
    for ln in bundle.lines:
        p = store().products[ln.product_id]
        if violations(p, prof):
            problems.append(f"{ln.product_id} sold despite {violations(p, prof)[0][0]}")
        if p.requires_one_of and not ids & set(p.requires_one_of):
            problems.append(f"{ln.product_id} sold without its dependency")
        if ln.unit_price != unit_price(p, prof.term_months):
            problems.append(f"{ln.product_id} mispriced")
    return not problems, problems, bundle.to_dict()


def run_all() -> list[dict]:
    out = []
    for s in SCENARIOS:
        ok, problems, bundle = _check(s)
        out.append({"id": s.id, "title": s.title, "says": s.says, "passed": ok, "problems": problems,
                    "products": [ln["product_id"] for ln in bundle["lines"]],
                    "refused": [{"product": e["product_id"], "rule": e["rule"]} for e in bundle["exclusions"]],
                    "monthly": bundle["monthly"]})
    return out
