"""Deterministic pricing inside the catalogue's price band.

Policy (documented in the business case):
  * 24-month commitment  -> catalogue floor (price_min)
  * shorter commitment   -> floor + 25% of the band, rounded to Rs 10
  * products whose minimum contract is already 24 months are always at the floor
  * the same online price applies whether the owner self-serves or a partner assists
  * prices exclude 18% GST; setup fees can be spread over 12 months at no cost
"""
from __future__ import annotations

from ..data_store import Product

GST_RATE = 0.18
SHORT_TERM_UPLIFT = 0.25


def unit_price(p: Product, term_months: int) -> int:
    if term_months >= 24 or p.min_contract >= 24:
        return p.price_min
    spread = p.price_max - p.price_min
    return p.price_min + int(round(spread * SHORT_TERM_UPLIFT / 10.0)) * 10


def contract_months(p: Product, term_months: int) -> int:
    """Monthly-billed products (min contract < 12) stay flexible on a 12-month plan."""
    if term_months >= 24:
        return max(24, p.min_contract)
    if p.min_contract >= 12:
        return max(p.min_contract, term_months)
    return p.min_contract


def gst(amount: int) -> int:
    return int(round(amount * GST_RATE))


def setup_emi(setup: int, months: int = 12) -> int:
    """The regular instalment; the last one absorbs the remainder (see schedule.instalments)."""
    return setup // months if setup else 0


def rupees(n: int) -> str:
    """Indian digit grouping: 123456 -> 1,23,456."""
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return ("-" if n < 0 else "") + "Rs " + s
