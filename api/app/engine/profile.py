"""The business profile the advisor fills in. Every field is optional until asked."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

QTY_KEYS = ("users", "devices", "cameras", "counters", "lines", "channels", "vehicles", "machines")
LANGUAGES = ("en", "hi", "mr", "ta", "te", "kn", "gu", "bn", "ml", "pa")
MAX_QTY = 500


@dataclass
class Profile:
    business_type: str | None = None
    segment: str | None = None  # micro | prof | multi | mfg
    employees: int | None = None
    sites: int | None = None
    city: str | None = None
    city_tier: int | None = None
    state: str | None = None
    pincode: str | None = None
    fibre_feasible: bool | None = None
    has_gstin: bool | None = None
    gstin: str | None = None
    gstin_status: str | None = None  # Active | Cancelled | Suspended | NotFound | Declared
    legal_name: str | None = None
    current_internet: str | None = None
    needs: set[str] = field(default_factory=set)
    excluded: set[str] = field(default_factory=set)  # needs the owner said no to: never added back as defaults
    only: bool = False  # owner wants only what they named, no suggestions
    qty: dict[str, int] = field(default_factory=dict)
    features: set[str] = field(default_factory=set)  # what a product must include: "roaming", "priority_support"
    data_gb: int | None = None  # mobile data per line the owner asked for
    speed_mbps: int | None = None
    uptime_pct: float | None = None
    budget: int | None = None
    current_spend: int | None = None  # what the owner pays today for phone/internet, per month (for "vs today")
    term_months: int = 12
    language: str = "en"

    # ---- derived -------------------------------------------------------------
    @property
    def gstin_ok(self) -> bool:
        """GST-only products need an active GSTIN. A declared-but-unverified one is
        accepted provisionally; Smart KYC verifies it before activation."""
        if self.gstin_status in ("Cancelled", "Suspended", "NotFound"):
            return False
        return bool(self.has_gstin) or self.gstin_status in ("Active", "Declared")

    @property
    def n_sites(self) -> int:
        return max(1, self.sites or 1)

    @property
    def n_employees(self) -> int:
        return max(1, self.employees or 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["needs"] = sorted(self.needs)
        d["excluded"] = sorted(self.excluded)
        d["features"] = sorted(self.features)
        return d

    @classmethod
    def from_dict(cls, d: dict | None) -> "Profile":
        if not d:
            return cls()
        d = dict(d)
        d["needs"] = set(d.get("needs") or [])
        d["excluded"] = set(d.get("excluded") or [])
        d["qty"] = dict(d.get("qty") or {})
        d["features"] = {f for f in (d.get("features") or []) if isinstance(f, str)}
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known}).sanitised()

    def sanitised(self) -> "Profile":
        """Clamp what an owner, a form or a model can type: no negative staff, sites or quantities."""
        def clamp(v, lo, hi):
            try:
                return None if v is None else max(lo, min(hi, int(v)))
            except (TypeError, ValueError):
                return None
        self.employees = clamp(self.employees, 1, 100000)
        self.sites = clamp(self.sites, 1, 1000)
        self.budget = clamp(self.budget, 1, 10_000_000)
        self.current_spend = clamp(self.current_spend, 0, 10_000_000)
        self.data_gb = clamp(self.data_gb, 1, 10_000)
        self.qty = {k: q for k, v in self.qty.items()
                    if k in QTY_KEYS and (q := clamp(v, 0, MAX_QTY))}  # zero or negative: dropped, not rounded up
        self.term_months = 24 if (self.term_months or 12) >= 24 else 12
        if self.city_tier not in (None, 1, 2, 3):
            self.city_tier = None
        return self

    def apply_needs(self, add: set[str], remove: set[str], replace: bool = False) -> bool:
        """Corrections stick: removed needs leave the profile and stay out of the defaults."""
        before = (set(self.needs), set(self.excluded))
        if replace and add:
            self.excluded |= self.needs - add
            self.needs = set(add)
        else:
            self.needs |= add
        self.needs -= remove
        self.excluded = (self.excluded | remove) - add
        return (self.needs, self.excluded) != before

    def missing(self) -> list[str]:
        """Slots the advisor still needs before it can recommend with confidence."""
        out = []
        if not self.business_type and not self.segment and not self.needs:
            out.append("business_type")
        if self.employees is None and not (self.only and self.needs <= {"mobile_lines", "website", "fleet"}):
            out.append("employees")
        if self.segment == "multi" and self.sites is None:
            out.append("sites")
        if self.city_tier is None:
            out.append("city")
        if self.has_gstin is None and self.gstin_status is None:
            out.append("gstin")
        return out
