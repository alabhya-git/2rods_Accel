"""Loads the official synthetic data pack once and exposes typed, read-only views.

Mock registries sit behind small lookup functions so they can be swapped for real
GSTN / Udyam / DigiLocker adapters without touching callers.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .config import get_settings

SEGMENTS = {
    "micro": "Micro retail & services",
    "prof": "Professional offices",
    "multi": "Small multi-site businesses",
    "mfg": "Small manufacturers",
}
SEGMENT_CODE = {v: k for k, v in SEGMENTS.items()}


@dataclass(frozen=True)
class Product:
    id: str
    category: str
    name: str
    description: str
    unit: str
    price_min: int
    price_max: int
    setup: int
    min_contract: int
    tiers: frozenset[int]
    min_employees: int
    min_sites: int
    requires_gstin: bool
    requires_one_of: tuple[str, ...]
    install_days: int
    segments: tuple[str, ...]


@dataclass
class DataStore:
    products: dict[str, Product]
    gstin: dict[str, dict]
    udyam: dict[str, dict]
    leads: list[dict]
    city_tier: dict[str, int]
    city_state: dict[str, str]
    business_segment: dict[str, str]
    # share of activated customers in a segment whose bundle contained the product
    take_rate: dict[tuple[str, str], float] = field(default_factory=dict)
    median_qty: dict[tuple[str, str], int] = field(default_factory=dict)


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _product(row: dict) -> Product:
    return Product(
        id=row["product_id"],
        category=row["category"],
        name=row["product_name"],
        description=row["description"],
        unit=row["unit"],
        price_min=int(row["price_min_inr_per_month"]),
        price_max=int(row["price_max_inr_per_month"]),
        setup=int(row["one_time_setup_inr"]),
        min_contract=int(row["min_contract_months"]),
        tiers=frozenset(int(t) for t in row["available_city_tiers"].split(";")),
        min_employees=int(row["min_employees"]),
        min_sites=int(row["min_sites"]),
        requires_gstin=row["requires_gstin"].strip().upper() == "Y",
        requires_one_of=tuple(p for p in row["requires_one_of"].split("|") if p),
        install_days=int(row["typical_install_days"]),
        segments=tuple(row["target_segments"].split(";")),
    )


@lru_cache
def store() -> DataStore:
    d = get_settings().data_dir
    products = {p.id: p for p in map(_product, _read(d / "product_catalogue.csv"))}
    gst = {r["gstin"]: r for r in _read(d / "mock_gstin_registry.csv")}
    udy = {r["udyam_number"]: r for r in _read(d / "mock_udyam_registry.csv")}
    leads = _read(d / "smb_leads.csv")

    city_tier: dict[str, int] = {}
    city_state: dict[str, str] = {}
    seg_votes: dict[str, Counter] = defaultdict(Counter)
    for r in leads:
        city_tier[r["city"]] = int(r["city_tier"])
        city_state[r["city"]] = r["state"]
        seg_votes[r["business_type"]][SEGMENT_CODE[r["segment"]]] += 1
    business_segment = {bt: c.most_common(1)[0][0] for bt, c in seg_votes.items()}

    take: dict[tuple[str, str], float] = {}
    qty: dict[tuple[str, str], list[int]] = defaultdict(list)
    seg_n: Counter = Counter()
    seg_has: Counter = Counter()
    for r in leads:
        if r["outcome"] != "Activated":
            continue
        seg = SEGMENT_CODE[r["segment"]]
        seg_n[seg] += 1
        for item in r["bundle_products"].split(";"):
            pid, q = item.split("x")
            seg_has[(seg, pid)] += 1
            qty[(seg, pid)].append(int(q))
    for (seg, pid), n in seg_has.items():
        take[(seg, pid)] = n / seg_n[seg]
    med = {k: sorted(v)[len(v) // 2] for k, v in qty.items()}

    return DataStore(products, gst, udy, leads, city_tier, city_state, business_segment, take, med)


# ---- registry adapters (mock) -------------------------------------------------

def lookup_gstin(gstin: str) -> dict | None:
    return store().gstin.get(gstin.strip().upper())


def lookup_udyam(number: str) -> dict | None:
    return store().udyam.get(number.strip().upper())


def find_gstin_by_name(name: str) -> list[dict]:
    n = name.strip().lower()
    return [r for r in store().gstin.values() if r["trade_name"].lower() == n or r["legal_name"].lower() == n]
