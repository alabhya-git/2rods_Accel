"""The payment schedule: the single source of every amount the owner sees or pays.

A quote version becomes a dated list of debits. Each row holds the recurring charges,
any setup instalment and GST, in integer paise. The quote screen, "due today", the
monthly figure, the total commitment, every charge and the UPI Autopay mandate limit
are all read from these rows and never recomputed anywhere else.

  * Row 0 is due today: the first month in advance, plus setup paid upfront or the
    first instalment.
  * Setup on EMI is split into whole-rupee instalments; the last absorbs the
    remainder, so instalments always sum exactly to the setup fee.
  * GST is applied by one rule (18%, rounded to the paisa) to every row.
  * The mandate limit is the largest scheduled debit.
"""
from __future__ import annotations

import hashlib
import json

GST_RATE_BP = 1800  # 18.00%, in basis points
EMI_MONTHS = 12


def _gst(paise: int) -> int:
    return (paise * GST_RATE_BP + 5000) // 10000  # round half up to the paisa


def instalments(setup_rupees: int, months: int = EMI_MONTHS) -> list[int]:
    """Whole-rupee instalments in paise; the last absorbs the remainder."""
    if setup_rupees <= 0:
        return []
    base = setup_rupees // months
    out = [base] * (months - 1) + [setup_rupees - base * (months - 1)]
    return [r * 100 for r in out]


def build(monthly_rupees: int, setup_rupees: int, term_months: int, setup_emi: bool) -> dict:
    term = max(1, int(term_months or 1))
    recurring = int(monthly_rupees) * 100
    setup = int(setup_rupees) * 100
    emi = instalments(setup_rupees) if setup_emi and setup else []
    rows = []
    for m in range(term):
        if emi:
            one_time = emi[m] if m < len(emi) else 0
        else:
            one_time = setup if m == 0 else 0
        tax = _gst(recurring) + _gst(one_time)
        rows.append({"month": m, "recurring": recurring, "setup": one_time, "gst": tax, "total": recurring + one_time + tax})
    # an EMI longer than the term is collected in the last scheduled month, never dropped
    if emi and len(emi) > term:
        rest = sum(emi[term:])
        last = rows[-1]
        last["setup"] += rest
        last["gst"] = _gst(last["recurring"]) + _gst(last["setup"])
        last["total"] = last["recurring"] + last["setup"] + last["gst"]
    due_today = rows[0]["total"]
    during = rows[1]["total"] if term > 1 else due_today
    after = recurring + _gst(recurring)
    body = {
        "currency": "INR", "unit": "paise", "term_months": term, "setup_emi": bool(emi),
        "rows": rows,
        "due_today": due_today,
        "monthly": during,                      # what each later debit is while instalments run
        "monthly_after_emi": after if emi else during,
        "emi_months": min(len(emi), term) if emi else 0,
        "instalment": emi[0] if emi else 0,
        "last_instalment": emi[-1] if emi else 0,
        "setup_total": setup,
        "total_commitment": sum(r["total"] for r in rows),
        "mandate_limit": max(r["total"] for r in rows),
    }
    body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    return body


def for_bundle(bundle: dict, setup_emi: bool) -> dict:
    term = max(int(bundle.get("contract_months") or 0), int(bundle.get("term_months") or 12))
    return build(int(bundle["monthly"]), int(bundle["setup"]), term, setup_emi)


def rupees(paise: int) -> str:
    """Rs 1,234 or Rs 1,234.56, Indian digit grouping."""
    from .pricing import rupees as whole
    r, p = divmod(int(paise), 100)
    return whole(r) + (f".{p:02d}" if p else "")
