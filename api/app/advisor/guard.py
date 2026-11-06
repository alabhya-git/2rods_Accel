"""The guard: an LLM reply may only name products and rupee amounts the rules engine produced."""
from __future__ import annotations

import re

from ..data_store import store

AMOUNT = re.compile(
    # greedy digits first: "Rs 6380" is 6380, not 638 (the old pattern's bug)
    r"(?:₹|rs\.?|inr|रु\.?|रुपये|ரூ\.?|రూ\.?|ರೂ\.?|રૂ\.?|টাকা|രൂ\.?|ਰੁ\.?)\s?(\d+(?:,\d{2,3})*(?:\.\d+)?)", re.I)


def allowed_amounts(bundle: dict | None, extra: set[int] | None = None) -> set[int]:
    nums: set[int] = set(extra or set())
    if bundle:
        for k in ("monthly", "monthly_other_term", "setup", "setup_emi", "gst_monthly", "first_payment"):
            if bundle.get(k) is not None:
                nums.add(int(bundle[k]))
        nums.add(int(bundle.get("monthly", 0)) + int(bundle.get("gst_monthly", 0)))
        nums.add(abs(int(bundle.get("monthly", 0)) - int(bundle.get("monthly_other_term", 0))))
        for ln in bundle.get("lines", []):
            nums.update({int(ln["unit_price"]), int(ln["monthly"]), int(ln["setup"])})
        for a in bundle.get("addons", []):
            nums.update({int(a["unit_price"]), int(a["monthly"]), int(a["setup"])})
        for n in bundle.get("notes", []):
            for k in ("budget", "monthly"):
                if n.get(k):
                    nums.add(int(n[k]))
    return nums


def check(text: str, bundle: dict | None, extra_amounts: set[int] | None = None, extra_products: set[str] | None = None) -> tuple[bool, list[str]]:
    issues: list[str] = []
    allowed = allowed_amounts(bundle, extra_amounts)
    for m in AMOUNT.finditer(text):
        value = int(float(m.group(1).replace(",", "")))
        if value not in allowed:
            issues.append(f"amount Rs {value} not produced by the rules engine")
    named = {ln["product_id"] for ln in (bundle or {}).get("lines", [])}
    named |= {e["product_id"] for e in (bundle or {}).get("exclusions", [])}
    named |= {a["product_id"] for a in (bundle or {}).get("addons", [])}
    named |= set(extra_products or set())
    low = text.lower()
    for p in store().products.values():
        if p.name.lower() in low and p.id not in named:
            issues.append(f"product '{p.name}' is not in the recommendation")
    if re.search(r"\bP\d{2}\b", text):
        issues.append("internal product code shown to the owner")
    return not issues, issues
