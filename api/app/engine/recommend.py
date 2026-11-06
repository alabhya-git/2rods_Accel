"""Deterministic bundle builder. The LLM never chooses products or prices: this does.

Every product added carries a reason; every product refused carries the rule that
refused it. That trace powers the "why this / why not" panel and the guard.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..data_store import Product, store
from . import graph
from .pricing import contract_months, gst, setup_emi, unit_price
from .profile import MAX_QTY, Profile

PER_SITE_ADDONS = ("P09", "P10", "P21", "P22")  # failover, SD-WAN, firewall, secure Wi-Fi

BUNDLE_NAMES = {
    "micro": "Dukaan Starter",
    "prof": "Clinic & Office Pro",
    "multi": "Multi-site One",
    "mfg": "Factory Connect",
}


@dataclass
class Line:
    product_id: str
    name: str
    category: str
    unit: str
    qty: int
    unit_price: int
    monthly: int
    setup: int
    contract_months: int
    install_days: int
    source: str  # asked | recommended | dependency | fallback
    need: str | None
    reason: dict


@dataclass
class Exclusion:
    product_id: str
    name: str
    rule: str
    args: dict
    alternative_id: str | None
    alternative_name: str | None
    need: str | None


@dataclass
class AddOn:
    need: str
    product_id: str
    name: str
    qty: int
    unit_price: int
    monthly: int
    setup: int
    eligible: bool
    rule: str | None
    args: dict


@dataclass
class Bundle:
    name: str
    segment: str | None
    term_months: int
    lines: list[Line]
    exclusions: list[Exclusion]
    addons: list[AddOn]
    monthly: int
    monthly_other_term: int
    setup: int
    setup_emi: int
    gst_monthly: int
    first_payment: int
    contract_months: int
    install_days: int
    notes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def product_ids(self) -> list[str]:
        return [ln.product_id for ln in self.lines]


# ---- rules -------------------------------------------------------------------

def violations(p: Product, prof: Profile) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    if prof.city_tier is not None and prof.city_tier not in p.tiers:
        out.append(("tier", {"tiers": sorted(p.tiers), "city": prof.city, "tier": prof.city_tier}))
    if p.min_employees > 1 and (prof.employees or 0) < p.min_employees:
        out.append(("min_employees", {"min": p.min_employees, "have": prof.employees}))
    if p.min_sites > 1 and prof.n_sites < p.min_sites:
        out.append(("min_sites", {"min": p.min_sites, "have": prof.n_sites}))
    if p.requires_gstin and not prof.gstin_ok:
        rule = "gstin_inactive" if prof.gstin_status in ("Cancelled", "Suspended") else "gstin_missing"
        out.append((rule, {"status": prof.gstin_status}))
    if p.id in graph.FIBRE and prof.fibre_feasible is False:
        out.append(("not_feasible", {"pincode": prof.pincode}))
    return out


def quantity(p: Product, prof: Profile) -> int:
    rule = graph.QTY_OVERRIDE.get(p.id) or graph.QTY_RULE.get(p.unit, "one")
    q = prof.qty
    seg = prof.segment or "micro"
    if rule == "sites":
        return prof.n_sites
    if rule == "users":
        return q.get("users") or min(prof.n_employees, 200)
    if rule == "devices":
        return q.get("devices") or q.get("users") or max(1, round(prof.n_employees * 0.5))
    if rule == "cameras":
        if q.get("cameras"):
            return q["cameras"]
        return {"mfg": 5, "multi": max(2, round(1.3 * prof.n_sites))}.get(seg, 2)
    if rule == "counters":
        return q.get("counters") or prof.n_sites
    if rule == "lines":
        if q.get("lines"):
            return q["lines"]
        return min({"micro": 2, "prof": 3, "multi": 4, "mfg": 4}[seg], prof.n_employees)
    if rule == "channels":
        return q.get("channels") or 3
    if rule == "vehicles":
        return q.get("vehicles") or 5
    if rule == "machines":
        return q.get("machines") or 10
    return 1


class _Builder:
    def __init__(self, prof: Profile):
        self.prof = prof
        self.ds = store()
        self.lines: dict[str, Line] = {}
        self.exclusions: list[Exclusion] = []
        self.notes: list[dict] = []

    # -- helpers --
    def P(self, pid: str) -> Product:
        return self.ds.products[pid]

    def exclude(self, pid: str, rule: str, args: dict, alt: str | None, need: str | None):
        if any(e.product_id == pid for e in self.exclusions):
            return
        self.exclusions.append(Exclusion(pid, self.P(pid).name, rule, args, alt, self.P(alt).name if alt else None, need))

    def add(self, pid: str, source: str, need: str | None, reason: dict):
        if pid in self.lines:
            return
        p = self.P(pid)
        qty = quantity(p, self.prof)
        up = unit_price(p, self.prof.term_months)
        self.lines[pid] = Line(
            pid, p.name, p.category, p.unit, qty, up, up * qty, p.setup * qty,
            contract_months(p, self.prof.term_months), p.install_days, source, need, reason,
        )

    def take(self, pid: str) -> int:
        seg = self.prof.segment
        return round(100 * self.ds.take_rate.get((seg, pid), 0.0)) if seg else 0

    # -- connectivity --
    def connectivity_chain(self, needs: set[str]) -> tuple[list[str], str]:
        prof = self.prof
        sla = "dedicated_line" in needs or (prof.uptime_pct or 0) >= 99.5
        if not needs & {"dedicated_line", "high_speed"} and prof.segment == "mfg" and prof.n_employees >= 10:
            sla = True
        gig = "high_speed" in needs or (prof.speed_mbps or 0) >= 1000
        if sla:
            big = (prof.uptime_pct or 0) >= 99.9 or (prof.speed_mbps or 0) >= 100
            return (["P06", "P05", "P02", "P01", "P04"] if big else ["P05", "P02", "P01", "P04"]), "sla"
        if gig:
            return ["P03", "P02", "P01", "P04"], "gig"
        if (prof.speed_mbps or 0) >= 300 or prof.n_employees >= 5 or prof.segment in ("prof", "multi", "mfg"):
            return ["P02", "P01", "P04"], "size"
        return ["P01", "P04"], "basic"

    def choose_connectivity(self, needs: set[str], source: str, reason_extra: dict | None = None) -> str | None:
        chain, why = self.connectivity_chain(needs)
        first = chain[0]
        explicit = bool(needs & {"dedicated_line", "high_speed"}) or why == "sla" and self.prof.uptime_pct
        for i, pid in enumerate(chain):
            v = violations(self.P(pid), self.prof)
            if not v:
                if i > 0 and (explicit or any(r == "not_feasible" for r, _ in violations(self.P(first), self.prof))):
                    rule, args = violations(self.P(first), self.prof)[0]
                    self.exclude(first, rule, args, pid, "internet")
                    reason = {"code": "fallback", "instead_of": first, "rule": rule}
                    src = "fallback"
                else:
                    reason = {"code": "connectivity", "why": why, **(reason_extra or {})}
                    src = source
                self.add(pid, src, "internet", reason)
                return pid
        return None

    # -- other needs --
    def pick(self, need: str, asked: bool) -> str | None:
        chain = graph.NEED_CHAIN[need]
        if need == "mobile_lines":
            chain = ("P07",) if (self.prof.segment in (None, "micro")) else ("P08", "P07")
        for pid in chain:
            v = violations(self.P(pid), self.prof)
            if not v:
                src = "asked" if asked else "recommended"
                reason = {"code": "asked", "need": need} if asked else {"code": "recommended", "segment": self.prof.segment, "pct": self.take(pid)}
                self.add(pid, src, need, reason)
                return pid
            if not asked:
                return None  # defaults that do not fit are skipped silently
            rule, args = v[0]
            alt = graph.FALLBACK.get(pid)
            if alt and alt not in self.lines and not violations(self.P(alt), self.prof):
                self.exclude(pid, rule, args, alt, need)
                self.add(alt, "fallback", need, {"code": "fallback", "instead_of": pid, "rule": rule})
                return alt
            self.exclude(pid, rule, args, alt if alt in self.lines else None, need)
            return None
        return None

    def resolve_dependencies(self, base: str | None, base_is_dependency: bool) -> None:
        changed = True
        while changed:
            changed = False
            for pid, ln in list(self.lines.items()):
                req = self.P(pid).requires_one_of
                if not req or any(r in self.lines for r in req):
                    continue
                if base is None:
                    base = self.choose_connectivity({"internet"}, "dependency", {"for": [ln.name]})
                    base_is_dependency = True
                    if base and base in req:
                        self.lines[base].source = "dependency"
                        self.lines[base].reason = {"code": "dependency", "for": [ln.name]}
                        changed = True
                        continue
                # cheapest eligible product from the required set
                options = sorted((self.P(r) for r in req if not violations(self.P(r), self.prof)), key=lambda p: p.price_min)
                if options:
                    self.add(options[0].id, "dependency", None, {"code": "dependency", "for": [ln.name]})
                else:
                    del self.lines[pid]
                    self.exclude(pid, "dependency_unmet", {"requires": [self.P(r).name for r in req]}, None, ln.need)
                changed = True
        # drop a dependency-only connection whose dependents were all refused
        if base and base_is_dependency and base in self.lines:
            dependents = [p for p in self.lines if base in self.P(p).requires_one_of]
            if not dependents:
                del self.lines[base]

    def fit_budget(self) -> None:
        budget = self.prof.budget
        if not budget:
            return

        def total() -> int:  # the owner's budget is what they pay: GST included
            m = sum(ln.monthly for ln in self.lines.values())
            return m + gst(m)

        def has_dependents(pid: str) -> bool:
            return any(pid in self.P(o).requires_one_of and not any(r in self.lines and r != pid for r in self.P(o).requires_one_of) for o in self.lines if o != pid)

        dropped: list[str] = []

        def drop_optional(max_take: int) -> None:
            while total() > budget:
                optional = [p for p, ln in self.lines.items()
                            if ln.source == "recommended" and p not in graph.CONNECTIVITY
                            and self.take(p) < max_take and not has_dependents(p)]
                if not optional:
                    return
                victim = min(optional, key=lambda p: (self.take(p), -self.lines[p].monthly))
                dropped.append(self.lines.pop(victim).name)

        # 1. extras fewer than half of similar customers bought
        drop_optional(50)
        # 2. fewer mobile lines
        for pid in ("P08", "P07"):
            ln = self.lines.get(pid)
            if ln and total() > budget and ln.qty > 1 and ln.source != "asked":
                ln.qty, ln.monthly = 1, ln.unit_price
                dropped.append(f"{ln.name} x1")
        # 3. cheaper equivalents
        for old, new in [("P08", "P07"), ("P03", "P02"), ("P02", "P01"), ("P01", "P04")]:
            if total() <= budget:
                break
            if old in self.lines and new not in self.lines and not violations(self.P(new), self.prof):
                blocked = any(old in self.P(o).requires_one_of and new not in self.P(o).requires_one_of
                              and not any(r in self.lines and r != old for r in self.P(o).requires_one_of)
                              for o in self.lines if o != old)
                if blocked:
                    continue
                ln = self.lines.pop(old)
                self.add(new, ln.source, ln.need, {"code": "budget", "instead_of": old})
                dropped.append(f"{self.P(old).name} -> {self.P(new).name}")
        # 4. any remaining suggestion
        drop_optional(101)
        if dropped:
            self.notes.append({"code": "budget_fit", "budget": budget, "changed": dropped})
        if total() > budget:
            self.notes.append({"code": "over_budget", "budget": budget, "monthly": total()})

    def cap_per_site(self) -> None:
        """A per-site add-on needs a connection at that site: units can't outnumber connected sites."""
        connected = sum(ln.qty for p, ln in self.lines.items() if p in graph.CONNECTIVITY)
        if not connected:
            return
        for pid in PER_SITE_ADDONS:
            ln = self.lines.get(pid)
            if ln and ln.qty > connected:
                self.notes.append({"code": "per_site_cap", "product": ln.name, "asked": ln.qty, "sites": connected})
                ln.qty, ln.monthly, ln.setup = connected, ln.unit_price * connected, self.P(pid).setup * connected


def build_addons(prof: Profile, chosen: set[str], needs: set[str]) -> list[AddOn]:
    if not prof.segment:
        return []
    ds = store()
    out = []
    for need in graph.SEGMENT_ADDONS[prof.segment]:
        if need in needs:
            continue
        chain = graph.NEED_CHAIN.get(need) or ()
        if not chain or chain[0] in chosen:
            continue
        p = ds.products[chain[0]]
        v = violations(p, prof)
        req_ok = not p.requires_one_of or any(r in chosen for r in p.requires_one_of)
        if not v and not req_ok:
            v = [("dependency_unmet", {"requires": [ds.products[r].name for r in p.requires_one_of]})]
        q = quantity(p, prof)
        up = unit_price(p, prof.term_months)
        out.append(AddOn(need, p.id, p.name, q, up, up * q, p.setup * q, not v, v[0][0] if v else None, v[0][1] if v else {}))
    return out


def recommend(prof: Profile) -> Bundle:
    b = _Builder(prof)
    asked = set(prof.needs) - prof.excluded
    needs = set(asked)
    if not prof.only and prof.segment:
        needs |= set(graph.SEGMENT_DEFAULTS[prof.segment])
        if prof.segment == "micro" and (prof.business_type or "").lower() in graph.COUNTER_BUSINESSES:
            needs.add("pos")
    needs -= prof.excluded  # a need the owner turned down never comes back as a default
    conn_needs = needs & {"internet", "high_speed", "dedicated_line"}
    base = None
    if conn_needs:
        src = "asked" if asked & conn_needs else "recommended"
        base = b.choose_connectivity(needs, src)
    for need in graph.PRIORITY:
        if need in needs and need not in ("internet", "high_speed", "dedicated_line"):
            b.pick(need, need in asked)
    b.resolve_dependencies(base, base_is_dependency=False)
    b.cap_per_site()
    b.fit_budget()

    # stable display order: connectivity, then catalogue order
    lines = sorted(b.lines.values(), key=lambda ln: (ln.product_id not in graph.CONNECTIVITY, ln.product_id))
    chosen = {ln.product_id for ln in lines}
    addons = build_addons(prof, chosen, needs)

    monthly = sum(ln.monthly for ln in lines)
    other = 12 if prof.term_months >= 24 else 24
    other_prof = Profile.from_dict({**prof.to_dict(), "term_months": other})
    monthly_other = sum(unit_price(b.P(ln.product_id), other_prof.term_months) * ln.qty for ln in lines)
    setup = sum(ln.setup for ln in lines)
    return Bundle(
        name=BUNDLE_NAMES.get(prof.segment or "", "Your Accel bundle"),
        segment=prof.segment,
        term_months=prof.term_months,
        lines=lines,
        exclusions=b.exclusions,
        addons=addons,
        monthly=monthly,
        monthly_other_term=monthly_other,
        setup=setup,
        setup_emi=setup_emi(setup),
        gst_monthly=gst(monthly),
        first_payment=monthly + gst(monthly) + setup + gst(setup),
        contract_months=max((ln.contract_months for ln in lines), default=0),
        install_days=max((ln.install_days for ln in lines), default=0),
        notes=b.notes,
    )


def price_custom(prof: Profile, items: dict[str, int]) -> Bundle:
    """Re-price an owner-edited bundle (add-ons toggled, quantities changed).
    Rules are re-checked: nothing ineligible can be bought by editing the cart."""
    b = _Builder(prof)
    for pid, qty in items.items():
        if pid not in b.ds.products or not isinstance(qty, int) or qty <= 0:
            continue
        qty = min(qty, MAX_QTY)
        v = violations(b.P(pid), prof)
        if v:
            b.exclude(pid, v[0][0], v[0][1], None, None)
            continue
        b.add(pid, "asked", None, {"code": "selected"})
        ln = b.lines[pid]
        ln.qty, ln.monthly, ln.setup = qty, ln.unit_price * qty, b.P(pid).setup * qty
    b.resolve_dependencies(next((p for p in b.lines if p in graph.CONNECTIVITY), None), False)
    b.cap_per_site()
    lines = sorted(b.lines.values(), key=lambda ln: (ln.product_id not in graph.CONNECTIVITY, ln.product_id))
    monthly = sum(ln.monthly for ln in lines)
    other = 12 if prof.term_months >= 24 else 24
    monthly_other = sum(unit_price(b.P(ln.product_id), other) * ln.qty for ln in lines)
    setup = sum(ln.setup for ln in lines)
    chosen = {ln.product_id for ln in lines}
    return Bundle(
        name=BUNDLE_NAMES.get(prof.segment or "", "Your Accel bundle"), segment=prof.segment, term_months=prof.term_months,
        lines=lines, exclusions=b.exclusions, addons=build_addons(prof, chosen, set(prof.needs)),
        monthly=monthly, monthly_other_term=monthly_other, setup=setup, setup_emi=setup_emi(setup),
        gst_monthly=gst(monthly), first_payment=monthly + gst(monthly) + setup + gst(setup),
        contract_months=max((ln.contract_months for ln in lines), default=0),
        install_days=max((ln.install_days for ln in lines), default=0), notes=b.notes,
    )
